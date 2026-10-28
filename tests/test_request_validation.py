"""Payment proposals cannot reduce spend by requesting zero or negative payments."""
import json

import pytest

from zeta_one.contracts import InvalidProposal
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.testing.replay import replay_engine, request_for


@pytest.mark.parametrize('amount', [0, -1, -499900])
def test_nonpositive_proposal_is_rejected_before_authorization(amount):
    scenario = load_fixture('routine_bill_payment')
    request = request_for(scenario)
    body = json.loads(request.body)
    body['amount']['amount'] = amount
    request.body = json.dumps(body).encode()
    engine = replay_engine(scenario)
    def forbidden(*args):
        raise AssertionError('invalid amount must not reach authorization or spend')
    engine.load_authorization = forbidden
    with pytest.raises(InvalidProposal, match='positive'):
        engine.evaluate(request)
