from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ObedienceApi

class ObedienceCoordinator(DataUpdateCoordinator[dict[str, list[dict[str, Any]]]]):
    def __init__(self, hass: HomeAssistant, api: ObedienceApi) -> None:
        self.api = api
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Obedience",
            update_interval=timedelta(minutes=15),
        )

    async def _async_update_data(self) -> dict[str, list[dict[str, Any]]]:
        try:
            return await self.api.get_all()
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def async_close(self) -> None:
        return
