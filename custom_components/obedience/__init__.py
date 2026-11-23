from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry, ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .api import ObedienceApi
from .const import (
    CONF_EXTENSION_ID,
    CONF_POLL_INTERVAL,
    CONF_SECRET,
    CONF_WEBHOOK_HABITS,
    CONF_WEBHOOK_PUNISHMENTS,
    CONF_WEBHOOK_RELATIONSHIPS,
    CONF_WEBHOOK_REWARDS,
    DEFAULT_WEBHOOK_SUBSCRIPTIONS,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ObedienceCoordinator
from .util import find_https_external_url
from .webhook import async_register_views

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {"pending": {}, "coordinators": {}})
    async_register_views(hass)

    async def _handle_increment_habit(call):
        habit_id = call.data.get("habit_id")
        amount = call.data["amount"]
        entity_ids = call.data.get("entity_id")
        if entity_ids and not habit_id:
            if isinstance(entity_ids, str):
                entity_ids = [entity_ids]
            entity_registry = er.async_get(hass)
            for entity_id in entity_ids:
                entity = entity_registry.async_get(entity_id)
                if not entity or entity.platform != DOMAIN or not entity.unique_id:
                    continue
                uid = entity.unique_id
                marker = "_habit_"
                if "_habits_" in uid:
                    habit_id = uid.split("_habits_", 1)[1]
                    break
                if marker in uid:
                    rest = uid.split(marker, 1)[1]
                    if rest.endswith("_increase"):
                        habit_id = rest[: -len("_increase")]
                        break
                    if rest.endswith("_decrease"):
                        habit_id = rest[: -len("_decrease")]
                        break
                    if rest.endswith("_positive"):
                        habit_id = rest[: -len("_positive")]
                        break
                    if "_metric_" in uid:
                        metric_rest = uid.split("_habit_metric_", 1)[1]
                        habit_id = metric_rest.rsplit("_", 1)[0]
                        break

        if not habit_id:
            raise HomeAssistantError(
                "Provide habit_id or an Obedience habit entity_id"
            )

        coordinators = hass.data.get(DOMAIN, {}).get("coordinators", {})
        for entry_id, coordinator in coordinators.items():
            if any(
                str(habit.get("id")) == str(habit_id)
                for habit in coordinator.data.get("habits", [])
            ):
                result = await coordinator.api.increment_habit(str(habit_id), int(amount))
                await coordinator.async_request_refresh()
                return {
                    "entry_id": entry_id,
                    "habit_id": str(habit_id),
                    "amount": int(amount),
                    "result": result,
                }
        raise HomeAssistantError(f"Unknown Obedience habit id: {habit_id}")

    hass.services.async_register(
        DOMAIN,
        "increment_habit",
        _handle_increment_habit,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {"pending": {}, "coordinators": {}})

    session = aiohttp_client.async_get_clientsession(hass)
    api = ObedienceApi(session, entry.data[CONF_EXTENSION_ID], entry.data[CONF_SECRET])

    poll_interval = entry.options.get(CONF_POLL_INTERVAL, 15)
    coordinator = ObedienceCoordinator(
        hass, api, config_entry=entry, poll_interval=poll_interval
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    external_url = find_https_external_url(hass)

    if external_url:
        webhook_url = (
            f"{external_url.rstrip('/')}/api/obedience/webhook/"
            f"{entry.data[CONF_EXTENSION_ID]}"
        )
        webhook_options = {
            **DEFAULT_WEBHOOK_SUBSCRIPTIONS,
            **entry.options,
        }
        try:
            await api.configure_webhook(
                webhook_url,
                habits=bool(webhook_options.get(CONF_WEBHOOK_HABITS, True)),
                rewards=bool(webhook_options.get(CONF_WEBHOOK_REWARDS, True)),
                punishments=bool(webhook_options.get(CONF_WEBHOOK_PUNISHMENTS, True)),
                relationships=bool(webhook_options.get(CONF_WEBHOOK_RELATIONSHIPS, True)),
            )
        except ConfigEntryAuthFailed:
            # Bad credentials: let Home Assistant start the reauth flow.
            raise
        except Exception as err:
            _LOGGER.warning(
                "Could not register the Obedience webhook for %s: %s",
                entry.title,
                err,
                exc_info=True,
            )
            ir.async_create_issue(
                hass,
                DOMAIN,
                f"webhook_registration_failed_{entry.entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="webhook_registration_failed",
                translation_placeholders={"entry": entry.title},
            )
        else:
            ir.async_delete_issue(
                hass, DOMAIN, f"webhook_registration_failed_{entry.entry_id}"
            )
            ir.async_delete_issue(hass, DOMAIN, f"no_external_url_{entry.entry_id}")
    else:
        _LOGGER.warning(
            "Obedience webhook not registered: no HTTPS external URL for entry %s",
            entry.entry_id,
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"no_external_url_{entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="no_external_url",
            translation_placeholders={"entry": entry.title},
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).get("coordinators", {}).pop(entry.entry_id, None)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, f"webhook_registration_failed_{entry.entry_id}")
    ir.async_delete_issue(hass, DOMAIN, f"no_external_url_{entry.entry_id}")


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version > 2:
        return False

    if entry.version < 2:
        entity_registry = er.async_get(hass)
        for entity in list(entity_registry.entities.values()):
            if entity.config_entry_id != entry.entry_id or entity.platform != DOMAIN:
                continue
            unique_id = entity.unique_id
            if not unique_id:
                continue
            new_unique_id: str | None = None
            if unique_id.startswith("obedience_diagnostic_"):
                new_unique_id = (
                    f"obedience_{entry.entry_id}_diagnostic_"
                    f"{unique_id[len('obedience_diagnostic_') :]}"
                )
            elif unique_id.startswith("obedience_habit_"):
                new_unique_id = (
                    f"obedience_{entry.entry_id}_habit_"
                    f"{unique_id[len('obedience_habit_') :]}"
                )
            elif unique_id.startswith("obedience_"):
                new_unique_id = (
                    f"obedience_{entry.entry_id}_{unique_id[len('obedience_') :]}"
                )
            if new_unique_id and new_unique_id != unique_id:
                try:
                    entity_registry.async_update_entity(
                        entity.entity_id, new_unique_id=new_unique_id
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Could not migrate unique id %s: %s", unique_id, err)

        hass.config_entries.async_update_entry(entry, version=2, minor_version=0)

    return True
