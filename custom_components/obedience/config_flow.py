from __future__ import annotations

import uuid
from urllib.parse import urlencode, urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_EXTENSION_ID,
    CONF_PUBLIC_URL,
    CONF_SECRET,
    CONF_UID,
    DOMAIN,
    NAME,
)


class ObedienceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            public_url = user_input[CONF_PUBLIC_URL].strip().rstrip("/")
            parsed = urlparse(public_url)

            if parsed.scheme != "https" or not parsed.netloc:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {vol.Required(CONF_PUBLIC_URL, default=public_url): str}
                    ),
                    errors={"base": "invalid_public_url"},
                )

            extension_id = str(uuid.uuid4())
            callback_url = f"{public_url}/api/obedience/callback"
            webhook_url = f"{public_url}/api/obedience/webhook/{extension_id}"

            auth_url = (
                "https://app.obedienceapp.com/home/extension-request?"
                + urlencode(
                    {
                        "id": extension_id,
                        "name": NAME,
                        "redirect": callback_url,
                    }
                )
            )

            self.hass.data[DOMAIN]["pending"][extension_id] = {
                CONF_PUBLIC_URL: public_url,
            }

            return self.async_show_form(
                step_id="authorize",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "auth_url": auth_url,
                    "callback_url": callback_url,
                    "webhook_url": webhook_url,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PUBLIC_URL): str}),
        )

    async def async_step_authorize(self, user_input=None):
        return self.async_abort(reason="authorization_started")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ObedienceOptionsFlow(config_entry)

    async def async_step_import(self, user_input=None):
        if not user_input:
            return self.async_abort(reason="auth_failed")

        uid = user_input[CONF_UID]
        extension_id = user_input[CONF_EXTENSION_ID]
        pending = self.hass.data[DOMAIN].get("pending", {}).get(extension_id)
        if not pending:
            return self.async_abort(reason="auth_failed")

        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Obedience",
            data={
                CONF_EXTENSION_ID: extension_id,
                CONF_SECRET: user_input[CONF_SECRET],
                CONF_UID: uid,
                CONF_PUBLIC_URL: pending[CONF_PUBLIC_URL],
            },
        )


class ObedienceOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
