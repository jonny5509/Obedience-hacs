from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ObedienceApi

_LOGGER = logging.getLogger(__name__)


class ObedienceCoordinator(DataUpdateCoordinator[dict[str, list[dict[str, Any]]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: ObedienceApi,
        config_entry: ConfigEntry | None = None,
        poll_interval: int = 15,
    ) -> None:
        self.api = api
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Obedience",
            update_interval=timedelta(minutes=poll_interval),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> dict[str, list[dict[str, Any]]]:
        try:
            return await self.api.get_all()
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(str(err)) from err
