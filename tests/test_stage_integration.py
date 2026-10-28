"""W1–W3 on the real kernel with synthetic data, fresh keys and no model calls."""
import sqlite3

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from zeta_one.authorization.check import checker
from zeta_one.authorization.store import Store as AuthorizationStore
from zeta_one.contracts import Authorization, Configuration, SignedRequest
from zeta_one.gateway.pipeline import Engine
from zeta_one.identity.registry import Registry
from zeta_one.identity.signing import sign, verifier
from zeta_one.rho.snapshot import Store
from zeta_one.rho.seed import SEED_NOW
from zeta_one.rho.view import context_for
from zeta_one.risk.tier0 import Tier0


def test_five_scenarios_with_real_data_identity_authorization_and_tier0(scenario):
    identity = scenario.decision_record.identity
    key = Ed25519PrivateKey.generate()
    connection = sqlite3.connect(':memory:')
    registry = Registry(connection)
    if identity.result != 'unknown_agent':
        registry.register(identity.claimed_agent_id, scenario.context.business.id,
                          identity.owner or 'synthetic-owner', key.public_key(), SEED_NOW)
    authorizations = AuthorizationStore(connection)
    snapshot = scenario.decision_record.authorization.snapshot
    if snapshot:
        authorizations.grant(Authorization.model_validate(snapshot))
    body = scenario.proposal.model_dump_json().encode()
    method, path = 'POST', '/v1/actions/propose_payment'
    request = SignedRequest(method=method, path=path, body=body,
        headers=sign(key, identity.claimed_agent_id, method, path, body, SEED_NOW))
    with Store() as store:
        engine = Engine(verifier(registry), authorizations.loader(), checker(lambda *_: 0),
                        context_for(store), Tier0(), clock=lambda: SEED_NOW,
                        configuration=Configuration(tiers=['tier0'], escalation='none'),
                        seed_version=store.seed_version)
        record, proposal = engine.evaluate(request)
        assert record.decision == scenario.scenario.expected
        assert record.identity.result == identity.result
        assert record.seed_version == store.seed_version
        assert record.execution.simulated is True
        if record.identity.result != 'verified' or record.authorization.violations:
            assert record.risk.tiers_run == []
        else:
            assert record.risk.tiers_run == ['tier0']
            assert proposal == scenario.proposal
        assert record.reasons == scenario.decision_record.reasons
    connection.close()
