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

        if resource == "relationships":
            # Do not use the Obedience UUID as the visible entity name.
            # The useful relationship details are exposed as state attributes.
            self._attr_name = "Relationship"
        else:
            self._attr_name = obj.get("name") or f"{RESOURCE_NAMES[resource]} {self.obj_id}"

    def _current_object(self) -> dict[str, Any] | None:
        return next(
            (
                obj
                for obj in self.coordinator.data.get(self.resource, [])
                if str(obj.get("id")) == self.obj_id
            ),
            None,
        )

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

        if self.resource == "relationships":
            return {
                "owner": obj.get("owner"),
                "partner": obj.get("partner"),
                "reward": obj.get("reward", 0),
                "history": obj.get("history"),
                "notes": obj.get("notes"),
            }

        return {
            key: value
            for key, value in obj.items()
            if key not in ("id", "name", "amount", "reward")
        }

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
