"""Verified outcomes (decision 0012): a person records what they found and how they know; only verified
findings count, outcomes are appended, and the stats report friction and missed fraud."""

import pytest

from tests.gateway.fakes import agent_headers, held_proposal, routine_proposal
from tests.gateway.test_app import ADMIN, client, gateway, hold, propose, world  # noqa: F401  (fixtures)


def report(client, decision_id, finding="payee_fraud", verification="bank_confirmation", headers=ADMIN, **extra):
    body = {"finding": finding, "verification": verification, "by": "controller", **extra}
    return client.post(f"/v1/decisions/{decision_id}/outcomes", json=body, headers=headers)


def stats(client):
    return client.get("/v1/stats", headers=ADMIN).json()


def test_a_disputed_allowed_payment_is_missed_fraud_once_verified(client):
    allowed = propose(client, routine_proposal()).json()
    response = report(client, allowed["decision_id"], note="vendor says they never received it")
    assert response.status_code == 201 and response.json()["verified"] is True
    assert stats(client)["missed_fraud"] == [allowed["decision_id"]]
    record = client.get(f"/v1/decisions/{allowed['decision_id']}", headers=ADMIN).json()
    assert record["outcomes"][0]["finding"] == "payee_fraud" and record["outcomes"][0]["source"] == "report"


def test_a_customer_report_alone_is_a_claim_not_a_label(client):
    allowed = propose(client, routine_proposal()).json()
    assert report(client, allowed["decision_id"], verification="customer_report").json()["verified"] is False
    numbers = stats(client)
    assert numbers["missed_fraud"] == [] and numbers["unverified_reports"] == 1
    assert numbers["verified_outcomes"]["payee_fraud"] == 0


def test_a_resolve_can_record_what_the_person_established(client):
    held = hold(client)
    body = {"outcome": "approve", "by": "owner", "finding": "legitimate", "verification": "callback_known_number",
            "note": "called the number on file"}
    assert client.post(f"/v1/challenges/{held['challenge_id']}/resolve", json=body, headers=ADMIN).status_code == 200
    record = client.get(f"/v1/decisions/{held['decision_id']}", headers=ADMIN).json()
    assert record["outcomes"][0]["source"] == "resolve" and record["outcomes"][0]["verified"] is True
    numbers = stats(client)
    assert numbers["unneeded_challenges"] == [held["decision_id"]]
    assert numbers["challenges"]["approval_rate"] == 1.0


def test_the_challenge_approval_rate_counts_resolved_challenges(client):
    for outcome in ("approve", "approve", "reject"):
        held = hold(client)
        client.post(f"/v1/challenges/{held['challenge_id']}/resolve", json={"outcome": outcome, "by": "o"}, headers=ADMIN)
    hold(client)  # still held
    challenges = stats(client)["challenges"]
    assert (challenges["total"], challenges["resolved"], challenges["approved"], challenges["rejected"]) == (4, 3, 2, 1)
    assert challenges["approval_rate"] == pytest.approx(2 / 3)


def test_outcomes_are_appended_and_the_latest_verified_one_counts(client):
    allowed = propose(client, routine_proposal()).json()
    report(client, allowed["decision_id"])
    report(client, allowed["decision_id"], finding="legitimate", verification="vendor_portal",
           note="the vendor's portal shows it received")
    record = client.get(f"/v1/decisions/{allowed['decision_id']}", headers=ADMIN).json()
    assert [o["finding"] for o in record["outcomes"]] == ["payee_fraud", "legitimate"]
    assert stats(client)["missed_fraud"] == []


def test_only_a_person_with_the_admin_token_records_an_outcome(client):
    allowed = propose(client, routine_proposal()).json()
    assert report(client, allowed["decision_id"], headers={}).status_code == 401
    assert report(client, allowed["decision_id"], headers={**ADMIN, **agent_headers()}).status_code == 403
    assert client.get("/v1/stats").status_code == 401


def test_bad_outcomes_are_refused(client):
    allowed = propose(client, routine_proposal()).json()
    assert report(client, "dec_nope").status_code == 404
    assert report(client, allowed["decision_id"], finding="probably_fine").status_code == 400
    assert report(client, allowed["decision_id"], verified=True).status_code == 400  # verified is derived, not claimed


def test_sandbox_scenario_runs_are_left_out_of_the_stats(client):
    client.post("/v1/scenarios/routine_bill_payment/run", json={})
    assert sum(stats(client)["decisions"].values()) == 0
