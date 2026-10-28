from datetime import datetime, timezone, timedelta
import sqlite3
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from zeta_one.contracts import SignedRequest
from zeta_one.identity.registry import Registry
from zeta_one.identity.signing import sign, verifier

NOW = datetime(2026, 10, 27, tzinfo=timezone.utc)

def test_signature_and_persistent_replay(tmp_path):
    path = tmp_path / 'identity.db'
    key = Ed25519PrivateKey.generate()
    registry = Registry(sqlite3.connect(path))
    registry.register('agent', 'business', 'owner', key.public_key(), NOW)
    headers = sign(key, 'agent', 'POST', '/pay', b'{}', NOW)
    request = SignedRequest(method='POST', path='/pay', body=b'{}', headers=headers)
    assert verifier(registry)(request, NOW).result == 'verified'
    assert verifier(Registry(sqlite3.connect(path)))(request, NOW).result == 'replay'

def test_outcomes_and_no_nonce_poisoning(tmp_path):
    key = Ed25519PrivateKey.generate()
    registry = Registry(sqlite3.connect(tmp_path / 'id.db'))
    registry.register('agent', 'business', 'owner', key.public_key(), NOW)
    verify = verifier(registry)
    headers = sign(key, 'agent', 'POST', '/pay', b'{}', NOW)
    request = SignedRequest(method='POST', path='/pay', body=b'changed', headers=headers)
    assert verify(request, NOW).result == 'invalid_signature'
    request.body = b'{}'
    assert verify(request, NOW).result == 'verified'
    assert verify(request.model_copy(update={'headers': {}}), NOW).result == 'unsigned'
    unknown = sign(key, 'unknown', 'POST', '/pay', b'{}', NOW)
    assert verify(request.model_copy(update={'headers': unknown}), NOW).result == 'unknown_agent'
    stale = sign(key, 'agent', 'POST', '/pay', b'{}', NOW - timedelta(seconds=301))
    assert verify(request.model_copy(update={'headers': stale}), NOW).result == 'stale_timestamp'
    registry.revoke('agent', NOW)
    assert verify(request, NOW).result == 'revoked'


import pytest

@pytest.mark.parametrize('seconds,status', [(-301,'stale_timestamp'),(-300,'verified'),(300,'verified'),(301,'stale_timestamp')])
def test_timestamp_boundaries(seconds,status):
    key = Ed25519PrivateKey.generate()
    registry = Registry(sqlite3.connect(':memory:'))
    registry.register('agent','business','owner',key.public_key(),NOW)
    headers = sign(key,'agent','POST','/pay',b'{}',NOW+timedelta(seconds=seconds))
    request = SignedRequest(method='POST',path='/pay',body=b'{}',headers=headers)
    assert verifier(registry)(request,NOW).result == status


def test_future_timestamp_nonce_survives_entire_valid_window():
    key = Ed25519PrivateKey.generate()
    registry = Registry(sqlite3.connect(':memory:'))
    registry.register('agent','business','owner',key.public_key(),NOW)
    headers = sign(key,'agent','POST','/pay',b'{}',NOW+timedelta(seconds=300))
    request = SignedRequest(method='POST',path='/pay',body=b'{}',headers=headers)
    verify = verifier(registry)
    assert verify(request,NOW).result == 'verified'
    assert verify(request,NOW+timedelta(seconds=600)).result == 'replay'
    assert verify(request,NOW+timedelta(seconds=601)).result == 'stale_timestamp'


@pytest.mark.parametrize('update', [{'method':'GET'}, {'path':'/other'}, {'body':b'{ }'}])
def test_signature_binds_method_path_and_exact_body(update):
    key = Ed25519PrivateKey.generate()
    registry = Registry(sqlite3.connect(':memory:'))
    registry.register('agent','business','owner',key.public_key(),NOW)
    headers = sign(key,'agent','POST','/pay',b'{}',NOW)
    request = SignedRequest(method='POST',path='/pay',body=b'{}',headers=headers)
    assert verifier(registry)(request.model_copy(update=update),NOW).result == 'invalid_signature'
    assert verifier(registry)(request,NOW).result == 'verified'
