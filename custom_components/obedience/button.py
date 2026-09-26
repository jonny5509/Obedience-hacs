from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ObedienceCoordinator


class ObedienceHabitButton(CoordinatorEntity[ObedienceCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        habit: dict[str, Any],
        amount: int,
    ) -> None:
        super().__init__(coordinator)
        self.habit_id = str(habit["id"])
        self.amount = amount

        direction = "increase" if amount > 0 else "decrease"
        self._attr_unique_id = f"obedience_habit_{self.habit_id}_{direction}"
        self._attr_name = (
            f"{direction.title()} {habit.get('name', self.habit_id)}"
        )
        self._attr_icon = (
            "mdi:plus-circle" if amount > 0 else "mdi:minus-circle"
        )

    async def async_press(self) -> None:
        await self.coordinator.api.increment_habit(self.habit_id, self.amount)
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
                    ObedienceHabitButton(coordinator, habit, amount)
                )

        if entities:
            async_add_entities(entities)

    add_new_entities()

    entry.async_on_unload(
        coordinator.async_add_listener(add_new_entities)
    )
