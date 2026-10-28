"""Admin access (security.md, S6).

Admin endpoints take `ZETA_ADMIN_TOKEN` as a bearer token and refuse any request that carries an
agent's signature headers, so no agent can approve its own payment.
"""

import hmac
import os
from collections.abc import Mapping
from pathlib import Path

from zeta_one.gateway.wiring import ROOT

AGENT_HEADER_PREFIX = "zeta-agent-"
AGENT_SIGNATURE_HEADERS = ("zeta-signature", "zeta-nonce", "zeta-timestamp")
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
    if any(name.lower().startswith(AGENT_HEADER_PREFIX) or name.lower() in AGENT_SIGNATURE_HEADERS for name in headers):
        raise AdminRefused(403, "agent_signed", "admin actions refuse agent-signed requests")
    if not token:
        raise AdminRefused(503, "admin_disabled", f"{TOKEN_NAME} is not set; run scripts/keygen.py")
    scheme, _, presented = (headers.get("authorization") or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(presented.encode(), token.encode()):
        raise AdminRefused(401, "bad_admin_token", "missing or wrong admin token")
