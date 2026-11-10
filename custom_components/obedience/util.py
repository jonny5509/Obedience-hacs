from __future__ import annotations

import logging

from homeassistant.components.cloud import CloudNotAvailable, async_remote_ui_url
from homeassistant.core import HomeAssistant
from homeassistant.helpers import network as ha_network

_LOGGER = logging.getLogger(__name__)


def find_https_external_url(hass: HomeAssistant) -> str | None:
    """Return the HTTPS external URL, however it is configured.

    Prefers the Home Assistant network settings (Settings > System > Network)
    and Nabu Casa via the network helper, then falls back to the legacy
    ``external_url`` YAML option. Returns ``None`` when nothing usable is
    configured.
    """
    candidates: list[str | None] = []

    try:
        candidates.append(ha_network.async_get_external_url(hass))
    except Exception as err:  # noqa: BLE001 - NoURLAvailableError or older HA layouts
        _LOGGER.debug("Network helper did not report an external URL: %s", err)

    legacy = getattr(getattr(hass, "config", None), "external_url", None)
    if isinstance(legacy, str):
        candidates.append(legacy)

    try:
        candidates.append(async_remote_ui_url(hass))
    except CloudNotAvailable:
        pass

    for url in candidates:
        if isinstance(url, str) and url.startswith("https://"):
            return url
    return None
