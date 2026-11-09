from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ObedienceCoordinator

RESOURCE_NAMES = {
    "habits": "Habit",
    "rewards": "Reward",
    "punishments": "Punishment",
    "relationships": "Relationship",
}

# Keys that are too large / noisy to expose as state attributes by default.
_LARGE_ATTRIBUTE_KEYS = {"history", "notes"}


class ObedienceObjectSensor(CoordinatorEntity[ObedienceCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        resource: str,
        obj: dict[str, Any],
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.resource = resource
        self.obj_id = str(obj["id"])
        self._entry_id = entry_id
        self._attr_unique_id = f"obedience_{entry_id}_{resource}_{self.obj_id}"

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
    def device_info(self) -> DeviceInfo:
        entry = getattr(self.coordinator, "config_entry", None)
        identifiers = (
            {(DOMAIN, entry.entry_id)}
            if entry is not None
            else {(DOMAIN, self._entry_id)}
        )
        name = "Obedience"
        if entry is not None and getattr(entry, "unique_id", None):
            name = f"Obedience ({entry.unique_id})"
        return DeviceInfo(
            identifiers=identifiers,
            name=name,
            manufacturer="Obedience",
            model="Obedience account",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

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
            return obj.get("reward")

        return obj.get("amount")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        obj = self._current_object()
        if obj is None:
            return {}

        attributes: dict[str, Any] = {}
        for key, value in obj.items():
            if key in _LARGE_ATTRIBUTE_KEYS:
                continue
            attributes[key] = value

        if self.resource == "relationships":
            attributes["nickname"] = self._relationship_nickname(obj)

        return attributes

    @property
    def icon(self) -> str:
        return {
            "habits": "mdi:check-circle-outline",
            "rewards": "mdi:gift-outline",
            "punishments": "mdi:gavel",
            "relationships": "mdi:account-heart-outline",
        }[self.resource]


class ObedienceDiagnosticSensor(CoordinatorEntity[ObedienceCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:database-search"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        resource: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.resource = resource
        self._entry_id = entry_id
        self._attr_unique_id = f"obedience_{entry_id}_diagnostic_{resource}"
        self._attr_name = f"API {RESOURCE_NAMES[resource]}s"

    @property
    def device_info(self) -> DeviceInfo:
        entry = getattr(self.coordinator, "config_entry", None)
        identifiers = (
            {(DOMAIN, entry.entry_id)}
            if entry is not None
            else {(DOMAIN, self._entry_id)}
        )
        name = "Obedience"
        if entry is not None and getattr(entry, "unique_id", None):
            name = f"Obedience ({entry.unique_id})"
        return DeviceInfo(
            identifiers=identifiers,
            name=name,
            manufacturer="Obedience",
            model="Obedience account",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get(self.resource, []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        objects = self.coordinator.data.get(self.resource, [])
        return {
            "resource": self.resource,
            "count": len(objects),
            "ids": [str(obj.get("id")) for obj in objects if obj.get("id") is not None],
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
                entities.append(
                    ObedienceObjectSensor(coordinator, resource, obj, entry.entry_id)
                )

        if entities:
            async_add_entities(entities)

    add_new_entities()

    async_add_entities(
        [
            ObedienceDiagnosticSensor(coordinator, resource, entry.entry_id)
            for resource in RESOURCE_NAMES
        ]
    )

    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))
