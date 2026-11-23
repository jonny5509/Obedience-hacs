from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from collections import deque
from typing import Any

from aiohttp import web
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.storage import Store

from .const import CONF_EXTENSION_ID, CONF_SECRET, CONF_UID, DOMAIN

_LOGGER = logging.getLogger(__name__)

_WEBHOOK_DEDUPE_TTL = 300  # seconds
_WEBHOOK_DEDUPE_MAX = 128
_WEBHOOK_DEDUPE_STORE_VERSION = 1
_WEBHOOK_DEDUPE_STORE_KEY = f"{DOMAIN}_webhook_dedupe"


async def _async_get_dedupe_store(hass) -> Store:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get("webhook_dedupe_store")
    if store is None:
        store = Store(hass, _WEBHOOK_DEDUPE_STORE_VERSION, _WEBHOOK_DEDUPE_STORE_KEY)
        domain_data["webhook_dedupe_store"] = store
    if not domain_data.get("webhook_dedupe_loaded"):
        loaded = await store.async_load() or {}
        dedupe = domain_data.setdefault("webhook_dedupe", {})
        now = time.time()
        for ext_id, entries in loaded.items():
            if not isinstance(entries, list):
                continue
            recent = dedupe.setdefault(ext_id, deque())
            for entry in entries:
                if (
                    isinstance(entry, dict)
                    and isinstance(entry.get("ts"), (int, float))
                    and isinstance(entry.get("key"), str)
                    and (now - float(entry["ts"])) <= _WEBHOOK_DEDUPE_TTL
                ):
                    recent.append((float(entry["ts"]), entry["key"]))
            while len(recent) > _WEBHOOK_DEDUPE_MAX:
                recent.popleft()
        domain_data["webhook_dedupe_loaded"] = True
    return store


async def _async_save_dedupe_store(hass) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get("webhook_dedupe_store")
    dedupe = domain_data.get("webhook_dedupe", {})
    if store is None:
        return
    now = time.time()
    payload: dict[str, list[dict[str, Any]]] = {}
    for ext_id, recent in dedupe.items():
        entries = [
            {"ts": ts, "key": key}
            for ts, key in recent
            if (now - ts) <= _WEBHOOK_DEDUPE_TTL
        ]
        if entries:
            payload[ext_id] = entries[-_WEBHOOK_DEDUPE_MAX:]
    await store.async_save(payload)


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

        await _async_get_dedupe_store(hass)
        dedupe_store = hass.data.setdefault(DOMAIN, {}).setdefault("webhook_dedupe", {})
        recent = dedupe_store.setdefault(extension_id, deque())
        now = time.time()
        while recent and (now - recent[0][0]) > _WEBHOOK_DEDUPE_TTL:
            recent.popleft()
        dedupe_key = hashlib.sha256(body).hexdigest()
        if any(key == dedupe_key for _, key in recent):
            _LOGGER.debug("Ignored duplicate Obedience webhook for %s", extension_id)
            return web.Response(status=204)
        recent.append((now, dedupe_key))
        while len(recent) > _WEBHOOK_DEDUPE_MAX:
            recent.popleft()
        try:
            await _async_save_dedupe_store(hass)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not persist Obedience webhook dedupe: %s", err)

        self._async_handle_payload(hass, coordinator, extension_id, payload)

        # Respond quickly; refresh in the background to respect the 10s timeout.
        async def _refresh() -> None:
            try:
                await coordinator.async_request_refresh()
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Obedience webhook refresh failed: %s", err)

        hass.async_create_task(_refresh())
        return web.Response(status=204)

    @staticmethod
    def _async_handle_payload(
        hass, coordinator, extension_id: str, payload: dict
    ) -> None:
        """Apply webhook payload to coordinator data and fire an HA event."""
        obj_type = payload.get("type")
        resource = {
            "habit": "habits",
            "reward": "rewards",
            "punishment": "punishments",
            "relationship": "relationships",
        }.get(obj_type)

        after = payload.get("after")
        before = payload.get("before")
        obj_id = None
        for candidate in (after, before):
            if isinstance(candidate, dict) and candidate.get("id") is not None:
                obj_id = str(candidate["id"])
                break

        if resource and coordinator.data is not None:
            items = list(coordinator.data.get(resource, []))
            changed = False
            if isinstance(after, dict) and after.get("id") is not None:
                after_id = str(after["id"])
                replaced = False
                for idx, item in enumerate(items):
                    if str(item.get("id")) == after_id:
                        items[idx] = after
                        replaced = True
                        break
                if not replaced:
                    items.append(after)
                changed = True
            elif (
                after is None
                and isinstance(before, dict)
                and before.get("id") is not None
            ):
                before_id = str(before["id"])
                new_items = [item for item in items if str(item.get("id")) != before_id]
                if len(new_items) != len(items):
                    items = new_items
                    changed = True

            if changed:
                new_data = dict(coordinator.data)
                new_data[resource] = items
                coordinator.async_set_updated_data(new_data)

        entry = getattr(coordinator, "config_entry", None)
        hass.bus.async_fire(
            f"{DOMAIN}_webhook",
            {
                "entry_id": entry.entry_id if entry is not None else None,
                "type": obj_type,
                "resource": resource,
                "extension_id": extension_id,
                "object_id": obj_id,
                "before": before if isinstance(before, dict) else None,
                "after": after if isinstance(after, dict) else None,
            },
        )
