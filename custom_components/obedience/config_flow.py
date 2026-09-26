from __future__ import annotations

import uuid
from urllib.parse import urlencode

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.cloud import CloudNotAvailable, async_remote_ui_url
from homeassistant.core import callback

from .const import CONF_EXTENSION_ID, CONF_SECRET, CONF_UID, DOMAIN, NAME
from .webhook import async_register_views


class ObedienceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._auth_data: dict[str, str] | None = None

    async def _async_start_authorization(self):
        async_register_views(self.hass)

        external_url = self.hass.config.external_url
        if not external_url or not external_url.startswith("https://"):
            try:
                external_url = async_remote_ui_url(self.hass)
            except CloudNotAvailable:
                external_url = None

        if not external_url or not external_url.startswith("https://"):
            return self.async_abort(reason="no_external_url")

        extension_id = str(uuid.uuid4())
        hass_data = self.hass.data.setdefault(
            DOMAIN,
            {"pending": {}, "coordinators": {}},
        )
        hass_data["pending"][extension_id] = self.flow_id

        callback_url = f"{external_url.rstrip('/')}/api/obedience/callback"
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

        return self.async_external_step(step_id="user", url=auth_url)

    async def async_step_user(self, user_input=None):
        return await self._async_handle_authorization(user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._async_handle_authorization(user_input)

    async def _async_handle_authorization(self, user_input=None):
        if user_input is not None:
            self._auth_data = {
                CONF_EXTENSION_ID: user_input[CONF_EXTENSION_ID],
                CONF_SECRET: user_input[CONF_SECRET],
                CONF_UID: user_input[CONF_UID],
            }

            if self.source == config_entries.SOURCE_RECONFIGURE:
                return self.async_external_step_done(next_step_id="finish")

            return self.async_external_step_done(next_step_id="finish")

        return await self._async_start_authorization()

    async def async_step_finish(self, user_input=None):
        if not self._auth_data:
            return self.async_abort(reason="auth_failed")

        if self.source == config_entries.SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            await self.async_set_unique_id(entry.unique_id)
            return self.async_update_reload_and_abort(
                entry,
                data_updates=self._auth_data,
            )

        uid = self._auth_data[CONF_UID]
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Obedience",
            data=self._auth_data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ObedienceOptionsFlow()

    async def async_step_import(self, user_input=None):
        if not user_input:
            return self.async_abort(reason="auth_failed")

        uid = user_input[CONF_UID]
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Obedience",
            data={
                CONF_EXTENSION_ID: user_input[CONF_EXTENSION_ID],
                CONF_SECRET: user_input[CONF_SECRET],
                CONF_UID: uid,
            },
        )


class ObedienceOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
