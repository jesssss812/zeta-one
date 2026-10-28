"""W1–W3 on the real kernel with synthetic data, fresh keys and no model calls."""
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from zeta_one.authorization.check import checker
from zeta_one.authorization.store import Store as AuthorizationStore
from zeta_one.contracts import MAX_PAYMENT_MINOR_UNITS, Authorization, Configuration, SignedRequest
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


def test_a_repeated_routine_payment_is_challenged_as_a_duplicate():
    """Through the gateway on real stages: the second identical payment sees the first in the ledger."""
    from datetime import timedelta

    from zeta_one.gateway.ledger import Ledger
    from zeta_one.gateway.service import Gateway
    from zeta_one.gateway.wiring import Stages

    from zeta_one.gateway.scenarios import load_fixture

    scenario = load_fixture('routine_bill_payment')
    identity = scenario.decision_record.identity
    key = Ed25519PrivateKey.generate()
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    connection.row_factory = sqlite3.Row
    registry = Registry(connection)
    registry.register(identity.claimed_agent_id, scenario.context.business.id, identity.owner or 'owner',
                      key.public_key(), SEED_NOW)
    authorizations = AuthorizationStore(connection)
    authorizations.grant(Authorization.model_validate(scenario.decision_record.authorization.snapshot))
    clock = [SEED_NOW]
    with Store() as store:
        stages = Stages(verify_identity=verifier(registry), load_authorization=authorizations.loader(),
                        make_checker=checker, load_context=context_for(store), tier0=Tier0(),
                        agent_status=lambda agent_id: 'active',
                        configuration=Configuration(tiers=['tier0'], escalation='none'))
        gateway = Gateway(stages=stages, ledger=Ledger(connection), clock=lambda: clock[0])
        body = scenario.proposal.model_dump_json().encode()
        decisions = []
        for _ in range(2):
            headers = sign(key, identity.claimed_agent_id, 'POST', '/v1/actions/propose_payment', body, clock[0])
            request = SignedRequest(method='POST', path='/v1/actions/propose_payment', body=body, headers=headers)
            decisions.append(gateway.propose(request))
            clock[0] += timedelta(minutes=5)
    assert [d['decision'] for d in decisions] == ['allow', 'challenge']
    record = gateway.ledger.decision(decisions[1]['decision_id'])
    assert record['risk']['features']['duplicate_candidate']['value'] is True
    assert 'duplicate_candidate' in record['risk']['floor']['flags']


@pytest.mark.parametrize('amount', [MAX_PAYMENT_MINOR_UNITS, MAX_PAYMENT_MINOR_UNITS + 1, 2**63, 10**400],
                         ids=['maximum', 'maximum-plus-one', 'past-sqlite', 'float-overflow'])
def test_signed_uncapped_payment_respects_the_supported_amount_range(amount):
    """End to end on real stages with no authorization caps: the largest amount is decided and written
    to the ledger; anything larger is a malformed request before authorization."""
    import json
    import math

    from zeta_one.contracts import InvalidProposal, Limits
    from zeta_one.gateway.ledger import Ledger
    from zeta_one.gateway.scenarios import load_fixture

    scenario = load_fixture('routine_bill_payment')
    identity = scenario.decision_record.identity
    key = Ed25519PrivateKey.generate()
    connection = sqlite3.connect(':memory:')
    registry = Registry(connection)
    registry.register(identity.claimed_agent_id, scenario.context.business.id, 'synthetic-owner',
                      key.public_key(), SEED_NOW)
    authorizations = AuthorizationStore(connection)
    authorization = Authorization.model_validate(scenario.decision_record.authorization.snapshot)
    authorization.limits = Limits()
    authorizations.grant(authorization)
    payload = scenario.proposal.model_dump(mode='json')
    payload['amount']['amount'] = amount
    body = json.dumps(payload).encode()
    method, path = 'POST', '/v1/actions/propose_payment'
    request = SignedRequest(method=method, path=path, body=body,
                            headers=sign(key, identity.claimed_agent_id, method, path, body, SEED_NOW))
    ledger = Ledger(connection)
    with Store() as store:
        engine = Engine(verifier(registry), authorizations.loader(), checker(ledger.spend_source()),
                        context_for(store), Tier0(), clock=lambda: SEED_NOW,
                        configuration=Configuration(tiers=['tier0'], escalation='none'))
        if amount > MAX_PAYMENT_MINOR_UNITS:
            with pytest.raises(InvalidProposal, match='too large'):
                engine.evaluate(request)
        else:
            record, proposal = engine.evaluate(request)
            assert record.identity.result == 'verified' and not record.authorization.violations
            assert record.decision == 'challenge'
            assert math.isfinite(record.risk.features['amount_ratio_to_vendor_median'].raw_value)
            ledger.record(record, proposal)
            assert connection.execute('SELECT amount FROM payments').fetchone()[0] == amount
    connection.close()


def test_a_bill_rho_already_paid_is_a_duplicate():
    """Naming a bill the seed shows as paid sets the duplicate floor, so it can't execute again."""
    from zeta_one.gateway.scenarios import load_fixture

    proposal = load_fixture('routine_bill_payment').proposal.model_copy(
        update={'bill_id': 'paid_txn_history_cp_0012_000', 'source_document_ids': []})
    with Store() as store:
        context = context_for(store)(proposal, 'biz_seed_01', SEED_NOW)
        assert context.bill.status == 'paid'
        assert all(record.bill_id for record in context.payment_history.recent)
        output = Tier0()(proposal, context, SEED_NOW)
    assert output.features['duplicate_candidate'].value is True
    assert 'paid_txn_history_cp_0012_000' in output.features['duplicate_candidate'].evidence
    assert output.result.level == 'elevated'


def test_a_bill_the_gateway_paid_leaves_the_open_bills():
    """Rho's stand-in records keep the bill open, so the gateway drops it itself; a later proposal
    without a bill reference then isn't challenged for not naming it."""
    from datetime import timedelta

    from zeta_one.gateway.ledger import Ledger
    from zeta_one.gateway.scenarios import load_fixture
    from zeta_one.gateway.service import with_gateway_payments

    scenario = load_fixture('routine_bill_payment')
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    connection.row_factory = sqlite3.Row
    ledger = Ledger(connection)
    record = scenario.decision_record.model_copy(update={'decision_id': 'dec_paid', 'created_at': SEED_NOW - timedelta(days=40)})
    ledger.record(record, scenario.proposal)
    with Store() as store:
        load = with_gateway_payments(context_for(store), ledger)
        context = load(scenario.proposal.model_copy(update={'bill_id': None, 'source_document_ids': []}),
                       'biz_seed_01', SEED_NOW)
    assert scenario.proposal.bill_id not in {bill.id for bill in context.open_bills}
    assert [p.bill_id for p in context.gateway_payments] == [scenario.proposal.bill_id]
