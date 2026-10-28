"""The recheck before a held payment executes (security.md, S9).

Approving a held payment reruns the deterministic checks on today's state; any change from the state
it was decided on blocks it.
"""

from datetime import datetime

from zeta_one.contracts import IdentityEvidence, InvalidProposal
from zeta_one.gateway.ledger import HeldPayment, Ledger, payment_method_state
from zeta_one.gateway.wiring import Stages


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
