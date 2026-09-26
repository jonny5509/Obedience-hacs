from __future__ import annotations

import base64
import hmac
import json

from aiohttp import web
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from homeassistant import config_entries
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
        if not extension_id or not secret or not uid or extension_id not in pending:
            return web.Response(status=400, text="Invalid Obedience authorization.")
        pending.pop(extension_id, None)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_EXTENSION_ID: extension_id, CONF_SECRET: secret, CONF_UID: uid},
        )
        if result["type"] == "abort":
            return web.Response(status=409, text=result.get("reason", "Authorization failed"))
        return web.HTTPFound("/config/integrations")

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
            (c for c in hass.data.get(DOMAIN, {}).get("coordinators", {}).values()
             if c.api.extension_id == extension_id), None
        )
        if coordinator is None or not hmac.compare_digest(payload.get("secret", ""), coordinator.api.secret):
            return web.Response(status=401, text="Unauthorized")
        signature = request.headers.get("X-Signature")
        if signature:
            try:
                public_key = serialization.load_pem_public_key(PUBLIC_KEY)
                public_key.verify(base64.b64decode(signature), body, padding.PKCS1v15(), hashes.SHA256())
            except Exception:
                return web.Response(status=401, text="Invalid signature")
        await coordinator.async_request_refresh()
        return web.Response(status=204)
