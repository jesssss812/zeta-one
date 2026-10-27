"""Admin access and the recheck before a held payment executes (security.md, S6 and S9).

Admin endpoints take `ZETA_ADMIN_TOKEN` as a bearer token and refuse any request that carries an
agent's signature headers, so no agent can approve its own payment. Approving a held payment reruns
the deterministic checks on today's state; any change from the state it was decided on blocks it.
"""

import hmac
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from zeta_one.contracts import IdentityEvidence, InvalidProposal
from zeta_one.gateway.ledger import HeldPayment, Ledger, payment_method_state
from zeta_one.gateway.wiring import ROOT, Stages

AGENT_HEADER_PREFIX = "zeta-agent-"
TOKEN_NAME = "ZETA_ADMIN_TOKEN"


class AdminRefused(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def admin_token(env_file: Path = ROOT / ".env") -> str | None:
    """The admin token from the environment, else from `.env`; None when neither has one."""
    if os.environ.get(TOKEN_NAME):
        return os.environ[TOKEN_NAME]
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == TOKEN_NAME and value.strip():
                return value.strip().strip("'\"")
    return None


def require_admin(headers: Mapping[str, str], token: str | None) -> None:
    """Raises AdminRefused unless the request is a person's, carrying the admin token."""
    if any(name.lower().startswith(AGENT_HEADER_PREFIX) for name in headers):
        raise AdminRefused(403, "agent_signed", "admin actions refuse agent-signed requests")
    if not token:
        raise AdminRefused(503, "admin_disabled", f"{TOKEN_NAME} is not set; run scripts/keygen.py")
    scheme, _, presented = (headers.get("authorization") or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(presented.encode(), token.encode()):
        raise AdminRefused(401, "bad_admin_token", "missing or wrong admin token")


def recheck(held: HeldPayment, identity: IdentityEvidence, stages: Stages, ledger: Ledger, now: datetime) -> list[str]:
    """What changed since a held payment was decided; empty when it may execute.

    Reruns agent status, authorization (status, expiry, scope, limits including rolling, with this
    payment left out of its own rolling total) and compares the payee's payment methods. A check
    that can't run counts as a change.
    """
    changes: list[str] = []

    status = stages.agent_status(held.agent_id) if stages.agent_status else None
    if status != "active":
        changes.append(f"agent:{status or 'unverifiable'}")

    if stages.load_authorization is None or stages.make_checker is None:
        changes.append("authorization:unverifiable")
    else:
        authorization = stages.load_authorization(held.business_id, held.agent_id)
        current = (authorization.authorization_id, authorization.version) if authorization else None
        if current != (held.authorization_id, held.authorization_version):
            changes.append("authorization:version")
        checker = stages.make_checker(ledger.spend_source(exclude=held.payment_id))
        evidence = checker(held.proposal, authorization, identity, now)
        changes += [f"authorization:{violation.field}" for violation in evidence.violations]

    if stages.load_context is None or held.payment_method_state is None:
        changes.append("payment_method:unverifiable")
    else:
        try:
            context = stages.load_context(held.proposal, held.business_id, now)
        except InvalidProposal:
            changes.append("payment_method:invalid")
        else:
            if payment_method_state(context) != held.payment_method_state:
                changes.append("payment_method:changed")

    return list(dict.fromkeys(changes))
