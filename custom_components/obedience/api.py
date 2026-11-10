from __future__ import annotations

import asyncio
import json
from typing import Any

from aiohttp import ClientSession, ClientTimeout
from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.exceptions import HomeAssistantError

from .const import API_BASE


class ObedienceApi:
    def __init__(
        self,
        session: ClientSession,
        extension_id: str,
        secret: str,
    ) -> None:
        self._session = session
        self.extension_id = extension_id
        self.secret = secret

    async def _request(self, method: str, resource: str, **kwargs: Any) -> Any:
        params = kwargs.pop("params", {})
        params = dict(params)
        params.update(
            {
                "extensionId": self.extension_id,
                "secret": self.secret,
            }
        )

        allow_non_json = kwargs.pop("allow_non_json", False)
        timeout = kwargs.pop("timeout", ClientTimeout(total=30))

        async with asyncio.timeout(30):
            async with self._session.request(
                method,
                f"{API_BASE}/{resource}",
                params=params,
                timeout=timeout,
                **kwargs,
            ) as response:
                if response.status >= 400:
                    text = await response.text()

                    if response.status == 401:
                        raise ConfigEntryAuthFailed(
                            "Obedience rejected the extension credentials. "
                            "Reauthorize the integration."
                        )

                    if (
                        response.status == 403
                        and method == "POST"
                        and resource == "habits"
                    ):
                        raise HomeAssistantError(
                            "Obedience denied this habit change. "
                            "The authenticated Obedience user does not have permission "
                            "to change this habit, or the habit requires photo proof. "
                            "The Obedience API does not allow the extension to "
                            "override that restriction."
                        )

                    raise HomeAssistantError(
                        f"Obedience API returned HTTP {response.status}: {text[:300]}"
                    )

                if response.status == 204:
                    return None

                text = await response.text()
                if not text.strip():
                    # Successful response with no body (e.g. webhook registration).
                    return None

                try:
                    return json.loads(text)
                except json.JSONDecodeError as err:
                    if allow_non_json:
                        # Some endpoints answer 200 with plain text such as "OK".
                        return text
                    raise HomeAssistantError(
                        f"Obedience API returned an invalid JSON response"
                        f" (HTTP {response.status}): {err}"
                    ) from err

    async def async_validate(self) -> None:
        """Perform a lightweight authenticated request to validate credentials."""
        await self._request("GET", "habits")

    async def get_all(self) -> dict[str, list[dict[str, Any]]]:
        resources = ("habits", "rewards", "punishments", "relationships")

        async def _fetch(resource: str) -> tuple[str, list[dict[str, Any]]]:
            data = await self._request("GET", resource)
            if not isinstance(data, list):
                data = []
            return resource, data

        results = await asyncio.gather(
            *(_fetch(resource) for resource in resources),
            return_exceptions=True,
        )

        result: dict[str, list[dict[str, Any]]] = {}
        for resource, fetched in zip(resources, results, strict=True):
            if isinstance(fetched, Exception):
                raise fetched
            _, data = fetched
            result[resource] = data
        return result

    async def increment_habit(self, habit_id: str, amount: int) -> Any:
        if amount == 0:
            raise ValueError("amount must not be zero")

        return await self._request(
            "POST",
            "habits",
            params={"id": habit_id},
            json={
                "action": "increment",
                "amount": amount,
            },
        )

    async def configure_webhook(self, webhook_url: str) -> Any:
        return await self._request(
            "POST",
            "webhook",
            allow_non_json=True,
            json={
                "url": webhook_url,
                "habits": True,
                "rewards": True,
                "punishments": True,
                "relationships": True,
            },
        )
