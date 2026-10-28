"""The recorded feedback-loop demo tells the story it claims, on the real stages, with no model call."""

from scripts import demo_loop


def test_the_loop_blocks_a_verified_fraud_account_and_lifts_a_confirmed_change_floor():
    loop = demo_loop.run(live_models=False)
    steps = {entry["title"]: entry for entry in loop["steps"]}
    assert loop["recorded"] and loop["simulated"] and not loop["live_models"]
    assert steps["A routine payment"]["decision"]["decision"] == "allow"
    assert steps["A customer reports fraud"]["outcome"]["verified"] is False
    assert steps["A customer reports fraud"]["adjustments"] == []
    [block] = steps["A reviewer verifies it"]["adjustments"]
    assert block["kind"] == "blocked_payment_method"
    again = steps["The agent pays that account again"]["decision"]
    assert again["decision"] == "block" and again["adjustments"] == [block["adjustment_id"]]
    held = steps["A payment after a recent bank change"]["decision"]
    assert held["floor"]["flags"] == ["payment_method_changed_days_ago"]
    later = steps["That vendor's next payment"]["decision"]
    assert later["floor"] is None and later["adjustments"]
    stats = steps["What the business sees"]["stats"]
    assert stats["missed_fraud"] == [steps["A routine payment"]["decision"]["decision_id"]]
    assert stats["unneeded_challenges"] == [held["decision_id"]] and stats["unverified_reports"] == 1
