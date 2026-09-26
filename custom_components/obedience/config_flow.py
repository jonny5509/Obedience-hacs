from __future__ import annotations

import uuid
from urllib.parse import urlencode

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_EXTENSION_ID, CONF_SECRET, CONF_UID, DOMAIN, NAME


class ObedienceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self.hass.config.external_url is None or not self.hass.config.external_url.startswith("https://"):
            return self.async_abort(reason="no_external_url")

        hass_data = self.hass.data.setdefault(DOMAIN, {"pending": {}, "coordinators": {}})
        extension_id = str(uuid.uuid4())
        callback_url = f"{self.hass.config.external_url.rstrip('/')}/api/obedience/callback"
        auth_url = (
            "https://app.obedienceapp.com/home/extension-request?"
            + urlencode({
                "id": extension_id,
                "name": NAME,
                "redirect": callback_url,
            })
        )
        hass_data["pending"][extension_id] = True

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={"auth_url": auth_url},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ObedienceOptionsFlow()

    async def async_step_import(self, user_input=None):
        if not user_input:
            return self.async_abort(reason="auth_failed")
        uid = user_input[CONF_UID]
        extension_id = user_input[CONF_EXTENSION_ID]
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Obedience",
            data={
                CONF_EXTENSION_ID: extension_id,
                CONF_SECRET: user_input[CONF_SECRET],
                CONF_UID: uid,
            },
        )


class ObedienceOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
