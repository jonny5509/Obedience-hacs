from __future__ import annotations

import base64
import hmac
import json

from aiohttp import web
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from homeassistant.components.http import HomeAssistantView

from .const import CONF_EXTENSION_ID, CONF_SECRET, CONF_UID, DOMAIN

PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDWZ6RbZ5cBGzxbe0/1/pJGkA62
JD4VREffIRfWHYHO+AE5P6EEis487pnLRR7eG5E+OvlYjtUVDF9eyuS866WR6L1h
C9N8hCV/N3ew2anTamfhNO7RIRRzMrFOz1wxJH9A+aEJVnuGg3SeRYzKWW7LPZ0Q
aP/+Yu9hK3pUPc1YCwIDAQAB
-----END PUBLIC KEY-----"""


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
        flow_id = pending.pop(extension_id, None)

        if not flow_id or not extension_id or not secret or not uid:
            return web.Response(
                status=400,
                text="Invalid Obedience authorization response.",
            )

        flow = hass.config_entries.flow.async_get(flow_id)
        if flow is None:
            return web.Response(
                status=404,
                text="Obedience authorization flow is no longer active. Start the Obedience setup again.",
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
        except Exception as err:
            return web.Response(
                status=500,
                text=f"Home Assistant could not complete the Obedience authorization: {err}",
            )

        if result["type"] != "external_step_done":
            return web.Response(
                status=500,
                text=f"Unexpected authorization flow result: {result['type']}",
            )

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
        except json.JSONDecodeError:
            return web.Response(status=400, text="Invalid JSON")

        coordinator = next(
            (
                c
                for c in hass.data.get(DOMAIN, {}).get("coordinators", {}).values()
                if c.api.extension_id == extension_id
            ),
            None,
        )
        if coordinator is None or not hmac.compare_digest(
            payload.get("secret", ""), coordinator.api.secret
        ):
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
            return web.Response(status=401, text="Invalid signature")

        await coordinator.async_request_refresh()
        return web.Response(status=204)
