"""Synthetic authorization documents and an in-memory spend fake."""
import sqlite3
from datetime import datetime, timezone, timedelta
from zeta_one.contracts import Authorization, IdentityEvidence, Proposal
from zeta_one.authorization.store import Store
from zeta_one.authorization.check import checker

NOW = datetime(2026, 10, 27, tzinfo=timezone.utc)

def auth(**updates):
    values = dict(authorization_id='auth', version=1, policy_version='test', business_id='biz',
                  agent_id='agent', granted_by='owner', granted_at=NOW,
                  limits={'per_payment': {'amount': 500000, 'currency': 'USD'},
                          'rolling': {'window_days': 7, 'amount': {'amount': 600000, 'currency': 'USD'}}})
    return Authorization(**(values | updates))

def proposal(amount=499900, currency='USD'):
    return Proposal(counterparty_id='cp', payment_method_id='pm', source_account_id='acct',
                    amount={'amount': amount, 'currency': currency})

IDENTITY = IdentityEvidence(result='verified', claimed_agent_id='agent', business_id='biz')

def test_caps_and_split_payments():
    spent = 0
    def spend(agent_id, since, currency):
        assert (agent_id, since, currency) == ('agent', NOW - timedelta(days=7), 'USD')
        return spent
    check = checker(spend)
    assert not check(proposal(500000), auth(), IDENTITY, NOW).violations
    assert not check(proposal(), auth(), IDENTITY, NOW).violations
    spent = 499900
    violations = check(proposal(), auth(), IDENTITY, NOW).violations
    assert [(v.field, v.kind) for v in violations] == [('limits.rolling', 'limit')]

def test_every_violation_and_currency():
    check = checker(lambda *args: 0)
    document = auth(actions=[], counterparties={'mode': 'allowlist', 'ids': []},
                    expires_at=NOW - timedelta(seconds=1), status='revoked', business_id='other', agent_id='other')
    fields = [v.field for v in check(proposal(currency='EUR'), document, IDENTITY, NOW).violations]
    assert fields == ['status', 'business_id', 'agent_id', 'actions', 'counterparties', 'expires_at',
                      'limits.per_payment', 'limits.rolling']
    assert len(fields) == len(set(fields))
    assert check(proposal(), None, IDENTITY, NOW).violations[0].kind == 'scope'

def test_store_versions_revocation_and_unknown_fields(tmp_path):
    path = tmp_path / 'auth.db'
    store = Store(sqlite3.connect(path))
    first = auth(future_constraint={'stored': True})
    store.grant(first)
    assert store.loader()('biz', 'agent').model_dump()['future_constraint'] == {'stored': True}
    store.grant(first.model_copy(update={'version': 2}))
    store.revoke('auth', NOW)
    reopened = Store(sqlite3.connect(path))
    assert reopened.loader()('biz', 'agent').status == 'revoked'
    assert reopened.loader()('biz', 'agent').version == 2


import pytest

@pytest.mark.parametrize('updates,field,kind', [
    ({'status':'revoked'}, 'status', 'scope'),
    ({'business_id':'other'}, 'business_id', 'scope'),
    ({'agent_id':'other'}, 'agent_id', 'scope'),
    ({'actions':[]}, 'actions', 'scope'),
    ({'counterparties':{'mode':'denylist','ids':['cp']}}, 'counterparties', 'scope'),
    ({'counterparties':{'mode':'allowlist','ids':['other']}}, 'counterparties', 'scope'),
    ({'expires_at':NOW}, 'expires_at', 'limit'),
    ({'limits':{'per_payment':{'amount':1,'currency':'USD'}}}, 'limits.per_payment', 'limit'),
    ({'limits':{'rolling':{'window_days':7,'amount':{'amount':1,'currency':'USD'}}}}, 'limits.rolling', 'limit'),
])
def test_each_constraint_independently(updates, field, kind):
    result = checker(lambda *args: 0)(proposal(), auth(**updates), IDENTITY, NOW)
    assert [(v.field, v.kind) for v in result.violations] == [(field, kind)]


def test_equal_rolling_cap_and_wrong_currency_do_not_mix_amounts():
    result = checker(lambda *args: 100100)(proposal(), auth(), IDENTITY, NOW)
    assert not result.violations
    def forbidden(*args):
        raise AssertionError('must not sum another currency')
    fields = [v.field for v in checker(forbidden)(proposal(currency='EUR'), auth(), IDENTITY, NOW).violations]
    assert fields == ['limits.per_payment', 'limits.rolling']


def test_older_grants_cannot_replace_latest(tmp_path):
    store = Store(sqlite3.connect(tmp_path / 'version.db'))
    store.grant(auth(version=2))
    with pytest.raises(ValueError, match='increase'):
        store.grant(auth(version=1))
    assert store.load('biz', 'agent').version == 2


def test_persisted_naive_expiry_fails_closed(tmp_path):
    store = Store(sqlite3.connect(tmp_path / 'naive-expiry.db'))
    expires_at = (NOW + timedelta(days=1)).replace(tzinfo=None)
    store.grant(auth(expires_at=expires_at))
    loaded = store.load('biz', 'agent')
    result = checker(lambda *args: 0)(proposal(), loaded, IDENTITY, NOW)
    assert [(v.field, v.kind) for v in result.violations] == [('expires_at', 'limit')]
    assert result.violations[0].limit == expires_at.isoformat()


def test_one_minor_unit_over_the_rolling_cap_is_a_violation():
    check = checker(lambda agent_id, since, currency: 100101)
    assert not checker(lambda *_: 100100)(proposal(), auth(), IDENTITY, NOW).violations  # exactly the cap
    assert [v.field for v in check(proposal(), auth(), IDENTITY, NOW).violations] == ['limits.rolling']
