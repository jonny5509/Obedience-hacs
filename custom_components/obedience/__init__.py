from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry, ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .api import ObedienceApi
from .const import CONF_EXTENSION_ID, CONF_POLL_INTERVAL, CONF_SECRET, DOMAIN, PLATFORMS
from .coordinator import ObedienceCoordinator
from .util import find_https_external_url
from .webhook import async_register_views

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {"pending": {}, "coordinators": {}})
    async_register_views(hass)

    async def _handle_increment_habit(call) -> None:
        habit_id = call.data["habit_id"]
        amount = call.data["amount"]
        coordinators = hass.data.get(DOMAIN, {}).get("coordinators", {})
        for coordinator in coordinators.values():
            if any(
                str(habit.get("id")) == str(habit_id)
                for habit in coordinator.data.get("habits", [])
            ):
                await coordinator.api.increment_habit(str(habit_id), int(amount))
                await coordinator.async_request_refresh()
                return
        raise HomeAssistantError(f"Unknown Obedience habit id: {habit_id}")

    hass.services.async_register(DOMAIN, "increment_habit", _handle_increment_habit)
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
        try:
            await api.configure_webhook(webhook_url)
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
