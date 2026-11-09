from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ObedienceCoordinator

_LOGGER = logging.getLogger(__name__)


class ObedienceHabitButton(CoordinatorEntity[ObedienceCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        habit: dict[str, Any],
        amount: int,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.habit_id = str(habit["id"])
        self.amount = amount
        self._entry_id = entry_id
        self._last_error: str | None = None

        direction = "increase" if amount > 0 else "decrease"
        self._attr_unique_id = f"obedience_{entry_id}_habit_{self.habit_id}_{direction}"
        self._attr_name = f"{direction.title()} {habit.get('name', self.habit_id)}"
        self._attr_icon = "mdi:plus-circle" if amount > 0 else "mdi:minus-circle"

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
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "habit_id": self.habit_id,
            "amount": self.amount,
        }
        if self._last_error:
            attributes["last_error"] = self._last_error
        return attributes

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.increment_habit(self.habit_id, self.amount)
        except Exception as err:
            self._last_error = str(err)
            self.async_write_ha_state()
            if isinstance(err, HomeAssistantError):
                raise
            raise HomeAssistantError(str(err)) from err

        self._last_error = None
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    known_ids: set[str] = set()

    def add_new_entities() -> None:
        entities = []

        for habit in coordinator.data.get("habits", []):
            if habit.get("id") is None:
                continue

            habit_id = str(habit["id"])
            for amount in (1, -1):
                direction = "increase" if amount > 0 else "decrease"
                key = f"{habit_id}:{direction}"

                if key in known_ids:
                    continue

                known_ids.add(key)
                entities.append(
                    ObedienceHabitButton(coordinator, habit, amount, entry.entry_id)
                )

        if entities:
            async_add_entities(entities)

    add_new_entities()

    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))
