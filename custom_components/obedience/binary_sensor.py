from __future__ import annotations

import contextlib
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ObedienceCoordinator


class ObedienceHabitPositiveBinarySensor(
    CoordinatorEntity[ObedienceCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        habit: dict[str, Any],
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.habit_id = str(habit["id"])
        self._entry_id = entry_id
        self._attr_unique_id = f"obedience_{entry_id}_habit_{self.habit_id}_positive"
        self._attr_name = f"{habit.get('name', self.habit_id)} Positive"
        self._attr_icon = "mdi:thumb-up-outline"

    def _current_habit(self) -> dict[str, Any] | None:
        return next(
            (
                habit
                for habit in self.coordinator.data.get("habits", [])
                if str(habit.get("id")) == self.habit_id
            ),
            None,
        )

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
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        return super().available and self._current_habit() is not None

    @property
    def is_on(self) -> bool | None:
        habit = self._current_habit()
        if habit is None:
            return None
        value = habit.get("positive")
        if isinstance(value, bool):
            return value
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        habit = self._current_habit() or {}
        return {
            "habit_id": self.habit_id,
            "goal": habit.get("goal"),
            "amount": habit.get("amount"),
        }


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    known_ids: set[str] = set()

    def _remove_stale_entities() -> None:
        registry = er.async_get(hass)
        prefix = f"obedience_{entry.entry_id}_habit_"
        current_ids = {
            str(habit.get("id"))
            for habit in coordinator.data.get("habits", [])
            if habit.get("id") is not None
        }
        for entity in list(registry.entities.values()):
            if (
                entity.config_entry_id != entry.entry_id
                or entity.platform != "binary_sensor"
                or not entity.unique_id
                or not entity.unique_id.startswith(prefix)
            ):
                continue
            if not entity.unique_id.endswith("_positive"):
                continue
            habit_id = entity.unique_id[len(prefix) : -len("_positive")]
            if habit_id not in current_ids:
                with contextlib.suppress(Exception):
                    registry.async_remove(entity.entity_id)

    def add_new_entities() -> None:
        entities = []
        for habit in coordinator.data.get("habits", []):
            if habit.get("id") is None:
                continue
            habit_id = str(habit["id"])
            if habit_id in known_ids:
                continue
            known_ids.add(habit_id)
            entities.append(
                ObedienceHabitPositiveBinarySensor(coordinator, habit, entry.entry_id)
            )
        if entities:
            async_add_entities(entities)
        _remove_stale_entities()

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))
