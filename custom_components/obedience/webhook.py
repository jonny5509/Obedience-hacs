from __future__ import annotations

import base64
import hmac
import json
import logging

from aiohttp import web
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from homeassistant.components.http import HomeAssistantView

from .const import CONF_EXTENSION_ID, CONF_SECRET, CONF_UID, DOMAIN

_LOGGER = logging.getLogger(__name__)

PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDWZ6RbZ5cBGzxbe0/1/pJGkA62
JD4VREffIRfWHYHO+AE5P6EEis487pnLRR7eG5E+OvlYjtUVDF9eyuS866WR6L1h
C9N8hCV/N3ew2anTamfhNO7RIRRzMrFOz1wxJH9A+aEJVnuGg3SeRYzKWW7LPZ0Q
aP/+Yu9hK3pUPc1YCwIDAQAB
-----END PUBLIC KEY-----"""


def async_register_views(hass) -> None:
    """Register HTTP views before the config entry exists."""
    key = f"{DOMAIN}_views_registered"
    if hass.data.get(key):
        return
    hass.http.register_view(ObedienceCallbackView)
    hass.http.register_view(ObedienceWebhookView)
    hass.data[key] = True


class ObedienceCallbackView(HomeAssistantView):
    url = "/api/obedience/callback"
    name = "api:obedience:callback"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        extension_id = request.query.get("id")
        secret = request.query.get("secret")
        uid = request.query.get("uid")

        pending = hass.data.get(DOMAIN, {}).get("pending", {})
        flow_id = pending.get(extension_id) if extension_id else None

        if not flow_id or not extension_id or not secret or not uid:
            return web.Response(
                status=400,
                text="Invalid Obedience authorization response.",
            )

        try:
            result = await hass.config_entries.flow.async_configure(
                flow_id,
                {
                    CONF_EXTENSION_ID: extension_id,
                    CONF_SECRET: secret,
                    CONF_UID: uid,
                },
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Obedience authorization callback failed: %s", err)
            return web.Response(
                status=500,
                text="Home Assistant could not complete the Obedience authorization.",
            )

        result_type = result.get("type") if isinstance(result, dict) else None
        if result_type not in ("external_done", "external_step_done"):
            return web.Response(
                status=500,
                text="Unexpected authorization flow result.",
            )

        pending.pop(extension_id, None)

        return web.Response(
            content_type="text/html",
            text=(
                "<!doctype html><html><head><title>Obedience connected</title></head>"
                "<body><p>Obedience connected. You can close this window.</p>"
                "<script>window.close()</script></body></html>"
            ),
        )


class ObedienceWebhookView(HomeAssistantView):
    url = "/api/obedience/webhook/{extension_id}"
    name = "api:obedience:webhook"
    requires_auth = False

    async def post(self, request: web.Request, extension_id: str) -> web.Response:
        hass = request.app["hass"]
        body = await request.read()

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return web.Response(status=400, text="Invalid JSON")

        if not isinstance(payload, dict):
            return web.Response(status=400, text="Invalid JSON")

        coordinator = next(
            (
                c
                for c in hass.data.get(DOMAIN, {}).get("coordinators", {}).values()
                if c.api.extension_id == extension_id
            ),
            None,
        )
        if coordinator is None:
            return web.Response(status=404, text="Unknown extension")

        if not hmac.compare_digest(
            str(payload.get("secret", "")), coordinator.api.secret
        ):
            return web.Response(status=401, text="Unauthorized")

        if payload.get("extensionId") not in (None, extension_id):
            return web.Response(status=401, text="Unauthorized")

        signature = request.headers.get("X-Signature")
        if not signature:
            return web.Response(status=401, text="Missing signature")

        try:
            public_key = serialization.load_pem_public_key(PUBLIC_KEY)
            public_key.verify(
                base64.b64decode(signature),
                body,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception:
            _LOGGER.debug("Invalid Obedience webhook signature", exc_info=True)
            return web.Response(status=401, text="Invalid signature")

        # Respond quickly; refresh in the background to respect the 10s timeout.
        async def _refresh() -> None:
            try:
                await coordinator.async_request_refresh()
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Obedience webhook refresh failed: %s", err)

        hass.async_create_task(_refresh())
        return web.Response(status=204)
