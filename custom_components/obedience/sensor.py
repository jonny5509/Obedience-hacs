from __future__ import annotations

import contextlib
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
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
        if resource == "relationships":
            self._attr_native_unit_of_measurement = "points"

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

    @staticmethod
    def _truncate_text(value: Any, limit: int = 500) -> str | None:
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value:
            return ""
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    def _relationship_summary_attributes(self, obj: dict[str, Any]) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        history = obj.get("history")
        if isinstance(history, list):
            attrs["history_count"] = len(history)
            last = history[-1] if history else None
            if isinstance(last, dict):
                attrs["last_history_amount"] = last.get("amount")
                attrs["last_history_reason"] = self._truncate_text(last.get("reason"), 200)
                attrs["last_history_manual"] = last.get("manual")
                date = last.get("date")
                if isinstance(date, dict):
                    attrs["last_history_date_seconds"] = date.get("_seconds")
        notes = obj.get("notes")
        if isinstance(notes, dict):
            for key in ("rules", "limits", "ideas", "notes"):
                note_data = notes.get(key)
                if isinstance(note_data, dict):
                    plain = self._truncate_text(note_data.get("plain_text"))
                    if plain is not None:
                        attrs[f"notes_{key}"] = plain
        return attrs

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
            attributes.update(self._relationship_summary_attributes(obj))

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


class ObedienceHabitMetricSensor(CoordinatorEntity[ObedienceCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        habit: dict[str, Any],
        entry_id: str,
        metric: str,
    ) -> None:
        super().__init__(coordinator)
        self.habit_id = str(habit["id"])
        self._entry_id = entry_id
        self.metric = metric
        self._attr_unique_id = f"obedience_{entry_id}_habit_metric_{self.habit_id}_{metric}"
        names = {
            "goal": "Goal",
            "remaining": "Remaining to goal",
            "progress": "Goal progress",
        }
        icons = {
            "goal": "mdi:target",
            "remaining": "mdi:flag-outline",
            "progress": "mdi:progress-check",
        }
        self._metric_names = names
        self._attr_icon = icons.get(metric, "mdi:chart-line")
        if metric == "progress":
            self._attr_native_unit_of_measurement = "%"

    @property
    def name(self) -> str:
        habit = self._current_habit()
        habit_name = (
            habit.get("name", self.habit_id) if habit else self.habit_id
        )
        return f"{habit_name} {self._metric_names.get(self.metric, self.metric)}"

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
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        return super().available and self._current_habit() is not None

    @property
    def native_value(self) -> Any:
        habit = self._current_habit()
        if habit is None:
            return None
        amount = habit.get("amount")
        goal = habit.get("goal")
        try:
            amount_f = float(amount) if amount is not None else None
            goal_f = float(goal) if goal is not None else None
        except (TypeError, ValueError):
            return None

        if self.metric == "goal":
            return goal_f
        if goal_f is None or amount_f is None:
            return None
        if self.metric == "remaining":
            return max(goal_f - amount_f, 0)
        if self.metric == "progress":
            if goal_f <= 0:
                return None
            return round(min(max((amount_f / goal_f) * 100, 0), 100), 1)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        habit = self._current_habit() or {}
        return {
            "habit_id": self.habit_id,
            "habit_name": habit.get("name"),
            "amount": habit.get("amount"),
            "goal": habit.get("goal"),
            "positive": habit.get("positive"),
        }


class ObedienceRewardMetricSensor(CoordinatorEntity[ObedienceCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ObedienceCoordinator,
        reward: dict[str, Any],
        entry_id: str,
        metric: str,
    ) -> None:
        super().__init__(coordinator)
        self.reward_id = str(reward["id"])
        self._entry_id = entry_id
        self.metric = metric
        self._attr_unique_id = f"obedience_{entry_id}_reward_metric_{self.reward_id}_{metric}"
        self._attr_icon = "mdi:cash" if metric == "cost" else "mdi:counter"

    def _current_reward(self) -> dict[str, Any] | None:
        return next(
            (
                reward
                for reward in self.coordinator.data.get("rewards", [])
                if str(reward.get("id")) == self.reward_id
            ),
            None,
        )

    @property
    def name(self) -> str:
        reward = self._current_reward()
        reward_name = reward.get("name", self.reward_id) if reward else self.reward_id
        label = "Cost" if self.metric == "cost" else self.metric.title()
        return f"{reward_name} {label}"

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
    def available(self) -> bool:
        return super().available and self._current_reward() is not None

    @property
    def native_value(self) -> Any:
        reward = self._current_reward()
        if reward is None:
            return None
        return reward.get(self.metric)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reward = self._current_reward() or {}
        return {
            "reward_id": self.reward_id,
            "reward_name": reward.get("name"),
            "amount": reward.get("amount"),
            "cost": reward.get("cost"),
        }


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    known_ids: set[str] = set()

    def _remove_stale_entities() -> None:
        registry = er.async_get(hass)
        prefix = f"obedience_{entry.entry_id}_"
        current_keys: set[str] = set()
        current_habit_metric_keys: set[str] = set()
        current_reward_metric_keys: set[str] = set()
        for resource in RESOURCE_NAMES:
            for obj in coordinator.data.get(resource, []):
                if obj.get("id") is not None:
                    current_keys.add(f"{resource}:{obj['id']}")
        for habit in coordinator.data.get("habits", []):
            if habit.get("id") is not None:
                habit_id = str(habit["id"])
                for metric in ("goal", "remaining", "progress"):
                    current_habit_metric_keys.add(f"{habit_id}:{metric}")
        for reward in coordinator.data.get("rewards", []):
            if reward.get("id") is not None:
                reward_id = str(reward["id"])
                for metric in ("cost",):
                    current_reward_metric_keys.add(f"{reward_id}:{metric}")

        for entity in list(registry.entities.values()):
            if (
                entity.config_entry_id != entry.entry_id
                or entity.platform != "sensor"
                or not entity.unique_id
                or not entity.unique_id.startswith(prefix)
            ):
                continue
            if "_diagnostic_" in entity.unique_id:
                continue
            rest = entity.unique_id[len(prefix) :]
            if rest.startswith("habit_metric_"):
                metric_rest = rest[len("habit_metric_") :]
                parts = metric_rest.rsplit("_", 1)
                if len(parts) == 2 and f"{parts[0]}:{parts[1]}" in current_habit_metric_keys:
                    continue
                with contextlib.suppress(Exception):
                    registry.async_remove(entity.entity_id)
                continue
            if rest.startswith("reward_metric_"):
                metric_rest = rest[len("reward_metric_") :]
                parts = metric_rest.rsplit("_", 1)
                if len(parts) == 2 and f"{parts[0]}:{parts[1]}" in current_reward_metric_keys:
                    continue
                with contextlib.suppress(Exception):
                    registry.async_remove(entity.entity_id)
                continue
            matched = False
            for resource in RESOURCE_NAMES:
                if rest.startswith(f"{resource}_"):
                    obj_id = rest[len(resource) + 1 :]
                    if f"{resource}:{obj_id}" in current_keys:
                        matched = True
                    break
            if not matched:
                with contextlib.suppress(Exception):
                    registry.async_remove(entity.entity_id)

    def add_new_entities() -> None:
        entities = []

        for resource in RESOURCE_NAMES:
            for obj in coordinator.data.get(resource, []):
                if obj.get("id") is None:
                    continue

                key = f"{resource}:{obj['id']}"
                if key not in known_ids:
                    known_ids.add(key)
                    entities.append(
                        ObedienceObjectSensor(coordinator, resource, obj, entry.entry_id)
                    )

                if resource == "habits":
                    habit_id = str(obj["id"])
                    for metric in ("goal", "remaining", "progress"):
                        metric_key = f"habit_metric:{habit_id}:{metric}"
                        if metric_key in known_ids:
                            continue
                        known_ids.add(metric_key)
                        entities.append(
                            ObedienceHabitMetricSensor(
                                coordinator, obj, entry.entry_id, metric
                            )
                        )

                if resource == "rewards":
                    reward_id = str(obj["id"])
                    for metric in ("cost",):
                        metric_key = f"reward_metric:{reward_id}:{metric}"
                        if metric_key in known_ids:
                            continue
                        known_ids.add(metric_key)
                        entities.append(
                            ObedienceRewardMetricSensor(
                                coordinator, obj, entry.entry_id, metric
                            )
                        )

        if entities:
            async_add_entities(entities)

        _remove_stale_entities()

    add_new_entities()

    async_add_entities(
        [
            ObedienceDiagnosticSensor(coordinator, resource, entry.entry_id)
            for resource in RESOURCE_NAMES
        ]
    )

    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))
