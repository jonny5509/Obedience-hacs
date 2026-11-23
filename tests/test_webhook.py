from __future__ import annotations

from types import SimpleNamespace

from custom_components.obedience.webhook import ObedienceWebhookView


class FakeBus:
    def __init__(self) -> None:
        self.events = []

    def async_fire(self, event_type, data):
        self.events.append((event_type, data))


class FakeCoordinator:
    def __init__(self) -> None:
        self.data = {
            "habits": [{"id": "h1", "amount": 1}],
            "rewards": [],
            "punishments": [],
            "relationships": [],
        }
        self.config_entry = SimpleNamespace(entry_id="entry1")
        self.updated = []

    def async_set_updated_data(self, data):
        self.data = data
        self.updated.append(data)


def test_webhook_payload_patches_and_fires_event() -> None:
    hass = SimpleNamespace(bus=FakeBus())
    coordinator = FakeCoordinator()
    payload = {
        "type": "habit",
        "extensionId": "ext1",
        "before": {"id": "h1", "amount": 1},
        "after": {"id": "h1", "amount": 2},
    }

    ObedienceWebhookView._async_handle_payload(hass, coordinator, "ext1", payload)

    assert coordinator.data["habits"][0]["amount"] == 2
    assert len(coordinator.updated) == 1
    assert hass.bus.events[0][0] == "obedience_webhook"
    assert hass.bus.events[0][1]["object_id"] == "h1"
    assert hass.bus.events[0][1]["after"]["amount"] == 2


def test_webhook_payload_removes_object_when_after_is_none() -> None:
    hass = SimpleNamespace(bus=FakeBus())
    coordinator = FakeCoordinator()
    payload = {
        "type": "habit",
        "extensionId": "ext1",
        "before": {"id": "h1", "amount": 1},
        "after": None,
    }

    ObedienceWebhookView._async_handle_payload(hass, coordinator, "ext1", payload)

    assert coordinator.data["habits"] == []
    assert hass.bus.events[0][1]["after"] is None
