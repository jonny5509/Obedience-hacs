from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ObedienceCoordinator

RESOURCE_NAMES = {"habits": "Habit", "rewards": "Reward", "punishments": "Punishment", "relationships": "Relationship"}

class ObedienceObjectSensor(CoordinatorEntity[ObedienceCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ObedienceCoordinator, resource: str, obj: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self.resource = resource
        self.obj_id = str(obj["id"])
        self._attr_unique_id = f"obedience_{resource}_{self.obj_id}"
        self._attr_name = obj.get("name") or f"{RESOURCE_NAMES[resource]} {self.obj_id}"

    @property
    def available(self) -> bool:
        return any(str(o.get("id")) == self.obj_id for o in self.coordinator.data.get(self.resource, []))

    @property
    def native_value(self):
        obj = next(o for o in self.coordinator.data.get(self.resource, []) if str(o.get("id")) == self.obj_id)
        return obj.get("reward", 0) if self.resource == "relationships" else obj.get("amount", 0)

    @property
    def extra_state_attributes(self):
        obj = next(o for o in self.coordinator.data.get(self.resource, []) if str(o.get("id")) == self.obj_id)
        return {k: v for k, v in obj.items() if k not in ("id", "name", "amount", "reward")}

    @property
    def icon(self):
        return {"habits": "mdi:check-circle-outline", "rewards": "mdi:gift-outline", "punishments": "mdi:gavel", "relationships": "mdi:account-heart-outline"}[self.resource]

async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    async_add_entities([ObedienceObjectSensor(coordinator, resource, obj)
                        for resource, objects in coordinator.data.items()
                        for obj in objects if obj.get("id") is not None])
