"""Ed25519 signatures over method, path and the raw body hash (decision 0006)."""
import base64
import binascii
import hashlib
import secrets
from datetime import datetime, timedelta
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from zeta_one.contracts import IdentityEvidence, IdentityVerifier, SignedRequest
from zeta_one.identity.registry import Registry

def _message(agent_id, timestamp, nonce, method, path, body):
    return '\n'.join((agent_id, timestamp, nonce, method.upper(), path, hashlib.sha256(body).hexdigest())).encode()

def sign(private_key: Ed25519PrivateKey, agent_id: str, method: str, path: str, body: bytes, now: datetime) -> dict[str, str]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('timestamp must be timezone-aware')
    timestamp, nonce = now.isoformat(), secrets.token_hex(16)
    signature = private_key.sign(_message(agent_id, timestamp, nonce, method, path, body))
    return {'Zeta-Agent-Id': agent_id, 'Zeta-Timestamp': timestamp, 'Zeta-Nonce': nonce,
            'Zeta-Signature': base64.b64encode(signature).decode()}

def verifier(registry: Registry) -> IdentityVerifier:
    def verify(request: SignedRequest, now: datetime) -> IdentityEvidence:
        headers = {key.lower(): value for key, value in request.headers.items()}
        agent_id, timestamp, nonce, signature = (headers.get(name) for name in
            ('zeta-agent-id', 'zeta-timestamp', 'zeta-nonce', 'zeta-signature'))
        evidence = IdentityEvidence(result='unsigned', claimed_agent_id=agent_id, timestamp=timestamp, nonce=nonce)
        def result(status):
            evidence.result = status
            return evidence
        if not all((agent_id, timestamp, nonce, signature)):
            return evidence
        evidence.checked.append('headers')
        agent = registry.get(agent_id)
        if agent is None:
            return result('unknown_agent')
        evidence.business_id, evidence.owner, evidence.key_id = agent.business_id, agent.owner, agent.agent_id
        evidence.checked.append('known_agent')
        if agent.status != 'active':
            return result('revoked')
        evidence.checked.append('active')
        try:
            signed_at = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if signed_at.tzinfo is None or abs((now - signed_at).total_seconds()) > 300:
                return result('stale_timestamp')
        except (ValueError, OverflowError, TypeError):
            return result('stale_timestamp')
        evidence.checked.append('timestamp')
        if registry.seen(agent_id, nonce, now):
            return result('replay')
        evidence.checked.append('nonce')
        try:
            Ed25519PublicKey.from_public_bytes(agent.public_key).verify(
                base64.b64decode(signature, validate=True),
                _message(agent_id, timestamp, nonce, request.method, request.path, request.body))
        except (InvalidSignature, ValueError, binascii.Error):
            return result('invalid_signature')
        if not registry.record_nonce(agent_id, nonce, signed_at + timedelta(seconds=300), now):
            return result('replay')
        evidence.checked.append('signature')
        return result('verified')
    return verify
