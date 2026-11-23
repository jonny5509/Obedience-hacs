from __future__ import annotations

import asyncio

from custom_components.obedience.api import ObedienceApi


class DummyApi(ObedienceApi):
    def __init__(self):
        self.calls = []

    async def _request(self, method, resource, **kwargs):
        self.calls.append((method, resource, kwargs))
        if resource == "habits" and kwargs.get("params", {}).get("id") == "h1":
            return {"id": "h1"}
        return []


def test_get_by_id_returns_dict() -> None:
    api = DummyApi()
    result = asyncio.run(api.get_by_id("habits", "h1"))
    assert result == {"id": "h1"}
    assert api.calls[0][2]["params"]["id"] == "h1"


def test_configure_webhook_passes_subscription_flags() -> None:
    api = DummyApi()
    asyncio.run(
        api.configure_webhook(
            "https://example.test/hook",
            habits=True,
            rewards=False,
            punishments=True,
            relationships=False,
        )
    )
    method, resource, kwargs = api.calls[0]
    assert method == "POST"
    assert resource == "webhook"
    assert kwargs["json"] == {
        "url": "https://example.test/hook",
        "habits": True,
        "rewards": False,
        "punishments": True,
        "relationships": False,
    }
