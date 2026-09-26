from __future__ import annotations

from typing import Any

from aiohttp import ClientSession
from homeassistant.exceptions import HomeAssistantError

from .const import API_BASE


class ObedienceApi:
    def __init__(self, session: ClientSession, extension_id: str, secret: str) -> None:
        self._session = session
        self.extension_id = extension_id
        self.secret = secret

    async def _request(self, method: str, resource: str, **kwargs: Any) -> Any:
        params = kwargs.pop("params", {})
        params.update({"extensionId": self.extension_id, "secret": self.secret})
        async with self._session.request(
            method, f"{API_BASE}/{resource}", params=params, **kwargs
        ) as response:
            if response.status >= 400:
                text = await response.text()
                raise HomeAssistantError(
                    f"Obedience API returned HTTP {response.status}: {text[:300]}"
                )
            return await response.json()

    async def get_all(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for resource in ("habits", "rewards", "punishments", "relationships"):
            result[resource] = await self._request("GET", resource)
        return result

    async def increment_habit(self, habit_id: str, amount: int) -> Any:
        if amount == 0:
            raise ValueError("amount must not be zero")
        return await self._request(
            "POST",
            "habits",
            params={"id": habit_id},
            json={"action": "increment", "amount": amount},
        )
