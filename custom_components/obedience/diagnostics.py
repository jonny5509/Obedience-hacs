from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_SECRET, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, redacting secrets."""
    coordinator = hass.data.get(DOMAIN, {}).get("coordinators", {}).get(entry.entry_id)
    data: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "options": dict(entry.options),
            "data": {
                key: ("***" if key == CONF_SECRET else value)
                for key, value in entry.data.items()
            },
        }
    }

    if coordinator is not None:
        try:
            data["coordinator_data"] = coordinator.data
        except Exception:  # noqa: BLE001
            data["coordinator_data"] = None

    return data
