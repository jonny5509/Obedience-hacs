from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.obedience import webhook


class FakeStore:
    def __init__(self, hass, version, key):
        self.saved = None
        self.data = {}

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = data


def test_dedupe_store_round_trip(monkeypatch) -> None:
    monkeypatch.setattr(webhook, "Store", FakeStore)
    hass = SimpleNamespace(data={})

    async def run():
        await webhook._async_get_dedupe_store(hass)
        dedupe = hass.data[webhook.DOMAIN]["webhook_dedupe"]
        dedupe.setdefault("ext1", webhook.deque()).append((webhook.time.time(), "abc"))
        await webhook._async_save_dedupe_store(hass)
        return hass.data[webhook.DOMAIN]["webhook_dedupe_store"].saved

    saved = asyncio.run(run())
    assert "ext1" in saved
    assert saved["ext1"][0]["key"] == "abc"
