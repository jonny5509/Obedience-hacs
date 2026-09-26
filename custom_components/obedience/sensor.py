from __future__ import annotations

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

        if self.resource == "relationships":
            return obj.get("reward", 0)

        return obj.get("amount", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        obj = self._current_object()
        if obj is None:
            return {}

        # Expose every field returned by the Obedience API. Nothing is
        # intentionally dropped so we can diagnose exactly what the API
        # provides for each object.
        attributes = dict(obj)

        if self.resource == "relationships":
            attributes["nickname"] = self._relationship_nickname(obj)

        # Keep the complete API object available in one clearly named field
        # as well, which makes nested/unexpected API fields easy to inspect.
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


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    known_ids: set[str] = set()

    def add_new_entities() -> None:
        entities = []
        for resource, objects in coordinator.data.items():
            for obj in objects:
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

    entry.async_on_unload(
        coordinator.async_add_listener(add_new_entities)
    )
