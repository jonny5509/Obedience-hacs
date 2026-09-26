from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import ObedienceApi
from .const import CONF_EXTENSION_ID, CONF_SECRET, CONF_UID, DOMAIN, PLATFORMS
from .coordinator import ObedienceCoordinator
from .webhook import ObedienceWebhookView, ObedienceCallbackView

type ObedienceConfigEntry = ConfigEntry

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {"pending": {}, "coordinators": {}})
    hass.http.register_view(ObedienceCallbackView)
    hass.http.register_view(ObedienceWebhookView)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp_client.async_get_clientsession(hass)
    api = ObedienceApi(
        session,
        entry.data[CONF_EXTENSION_ID],
        entry.data[CONF_SECRET],
    )
    coordinator = ObedienceCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = hass.data[DOMAIN]["coordinators"].pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_close()
    return unloaded
