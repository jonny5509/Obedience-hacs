from __future__ import annotations

from custom_components.obedience.sensor import ObedienceObjectSensor


def test_truncate_text() -> None:
    assert ObedienceObjectSensor._truncate_text("hello", 10) == "hello"
    assert ObedienceObjectSensor._truncate_text("hello world", 8) == "hello..."


def test_relationship_summary_attributes() -> None:
    sensor = object.__new__(ObedienceObjectSensor)
    obj = {
        "history": [
            {
                "amount": 1,
                "reason": "did thing",
                "manual": False,
                "date": {"_seconds": 1700000000, "_nanoseconds": 0},
            }
        ],
        "notes": {
            "rules": {"plain_text": "Be good", "rich_text": "{}"},
            "limits": {"plain_text": "", "rich_text": "{}"},
        },
    }

    attrs = sensor._relationship_summary_attributes(obj)

    assert attrs["history_count"] == 1
    assert attrs["last_history_amount"] == 1
    assert attrs["last_history_reason"] == "did thing"
    assert attrs["last_history_manual"] is False
    assert attrs["last_history_date_seconds"] == 1700000000
    assert attrs["notes_rules"] == "Be good"
    assert attrs["notes_limits"] == ""


def test_reward_metric_cost_sensor() -> None:
    from custom_components.obedience.sensor import ObedienceRewardMetricSensor

    sensor = object.__new__(ObedienceRewardMetricSensor)
    sensor.metric = "cost"
    sensor.reward_id = "r1"
    sensor.coordinator = type(
        "C", (), {"data": {"rewards": [{"id": "r1", "name": "R", "amount": 2, "cost": 10}]}}
    )()

    assert sensor.native_value == 10
    assert sensor.name == "R Cost"
