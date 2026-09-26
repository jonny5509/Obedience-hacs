from __future__ import annotations

import uuid
from urllib.parse import urlencode

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_EXTENSION_ID, CONF_SECRET, CONF_UID, DOMAIN, NAME

AUTH_REDIRECT_URL = "https://jonny5509.github.io/Obedience-hacs/authorize.html"


class ObedienceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        extension_id = str(uuid.uuid4())
        auth_url = (
            "https://app.obedienceapp.com/home/extension-request?"
            + urlencode(
                {"id": extension_id, "name": NAME, "redirect": AUTH_REDIRECT_URL}
            )
        )
        self.hass.data[DOMAIN]["pending"][extension_id] = True

        return self.async_show_form(
            step_id="authorize",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EXTENSION_ID, default=extension_id): str,
                    vol.Required(CONF_SECRET): str,
                    vol.Required(CONF_UID): str,
                }
            ),
            description_placeholders={"auth_url": auth_url},
        )

    async def async_step_authorize(self, user_input=None):
        if not user_input:
            return self.async_abort(reason="auth_failed")

        extension_id = user_input[CONF_EXTENSION_ID].strip()
        if not self.hass.data[DOMAIN]["pending"].pop(extension_id, None):
            return self.async_abort(reason="auth_failed")

        await self.async_set_unique_id(user_input[CONF_UID].strip())
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Obedience",
            data={
                CONF_EXTENSION_ID: extension_id,
                CONF_SECRET: user_input[CONF_SECRET].strip(),
                CONF_UID: user_input[CONF_UID].strip(),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ObedienceOptionsFlow(config_entry)


class ObedienceOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
