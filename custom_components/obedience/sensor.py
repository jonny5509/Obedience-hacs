from __future__ import annotations

import json
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ObedienceCoordinator

RESOURCE_NAMES = {
    "habits": "Habit",
    "rewards": "Reward",
    "punishments": "Punishment",
    "relationships": "Relationship",
}


class ObedienceObjectSensor(CoordinatorEntity[ObedienceCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        resource: str,
        obj: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self.resource = resource
        self.obj_id = str(obj["id"])
        self._attr_unique_id = f"obedience_{resource}_{self.obj_id}"

    def _current_object(self) -> dict[str, Any] | None:
        return next(
            (
                obj
                for obj in self.coordinator.data.get(self.resource, [])
                if str(obj.get("id")) == self.obj_id
            ),
            None,
        )

    def _relationship_nickname(self, obj: dict[str, Any]) -> str | None:
        for key in ("partner_nickname", "nickname", "partner_name"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        partner = obj.get("partner")
        if isinstance(partner, dict):
            for key in ("nickname", "name", "displayName", "display_name"):
                value = partner.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return None

    @staticmethod
    def _is_valid_value(value: Any) -> bool:
        return value is not None and not (
            isinstance(value, str) and value.strip().lower() in {"", "unknown", "unavailable", "none", "null"}
        )

    @staticmethod
    def _history_value(obj: dict[str, Any]) -> tuple[Any, Any] | None:
        """Return the newest valid amount in history, when the API includes it."""
        history = obj.get("history")
        if not isinstance(history, list):
            return None

        candidates = []
        for entry in history:
            if not isinstance(entry, dict) or not ObedienceObjectSensor._is_valid_value(entry.get("amount")):
                continue

            date = entry.get("date")
            if isinstance(date, dict):
                seconds = date.get("_seconds", 0)
                nanos = date.get("_nanoseconds", 0)
                try:
                    timestamp = float(seconds) + float(nanos) / 1_000_000_000
                except (TypeError, ValueError):
                    timestamp = 0
            else:
                timestamp = 0

            candidates.append((timestamp, entry.get("amount"), date))

        if not candidates:
            return None

        _, amount, date = max(candidates, key=lambda item: item[0])
        return amount, date

    def _value_key(self) -> str:
        return "reward" if self.resource == "relationships" else "amount"

    @property
    def name(self) -> str:
        obj = self._current_object()

        if self.resource == "relationships":
            nickname = self._relationship_nickname(obj or {})
            return nickname or "Relationship"

        if obj:
            return obj.get("name") or f"{RESOURCE_NAMES[self.resource]} {self.obj_id}"

        return f"{RESOURCE_NAMES[self.resource]} {self.obj_id}"

    @property
    def available(self) -> bool:
        return super().available and self._current_object() is not None

    @property
    def native_value(self) -> Any:
        obj = self._current_object()
        if obj is None:
            return None

        current_value = obj.get(self._value_key())
        if self._is_valid_value(current_value):
            return current_value

        history_value = self._history_value(obj)
        if history_value is not None:
            return history_value[0]

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        obj = self._current_object()
        if obj is None:
            return {}

        attributes = dict(obj)
        current_value = obj.get(self._value_key())
        history_value = self._history_value(obj)
        if not self._is_valid_value(current_value) and history_value is not None:
            attributes["value_source"] = "history"
            attributes["history_value_date"] = history_value[1]
        else:
            attributes["value_source"] = "current_api"

        if self.resource == "relationships":
            attributes["nickname"] = self._relationship_nickname(obj)

        attributes["api_data"] = dict(obj)
        return attributes

    @property
    def icon(self) -> str:
        return {
            "habits": "mdi:check-circle-outline",
            "rewards": "mdi:gift-outline",
            "punishments": "mdi:gavel",
            "relationships": "mdi:account-heart-outline",
        }[self.resource]


class ObedienceDiagnosticSensor(
    CoordinatorEntity[ObedienceCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_icon = "mdi:database-search"

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        resource: str,
    ) -> None:
        super().__init__(coordinator)
        self.resource = resource
        self._attr_unique_id = f"obedience_diagnostic_{resource}"
        self._attr_name = f"API {RESOURCE_NAMES[resource]}s"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get(self.resource, []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        objects = self.coordinator.data.get(self.resource, [])
        return {
            "resource": self.resource,
            "count": len(objects),
            "ids": [
                str(obj.get("id"))
                for obj in objects
                if obj.get("id") is not None
            ],
            "api_objects": json.dumps(objects, default=str),
        }


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    known_ids: set[str] = set()

    def add_new_entities() -> None:
        entities = []

        for resource in RESOURCE_NAMES:
            for obj in coordinator.data.get(resource, []):
                if obj.get("id") is None:
                    continue

                key = f"{resource}:{obj['id']}"
                if key in known_ids:
                    continue

                known_ids.add(key)
                entities.append(ObedienceObjectSensor(coordinator, resource, obj))

        if entities:
            async_add_entities(entities)

    add_new_entities()

    async_add_entities(
        [
            ObedienceDiagnosticSensor(coordinator, resource)
            for resource in RESOURCE_NAMES
        ]
    )

    entry.async_on_unload(
        coordinator.async_add_listener(add_new_entities)
    )
