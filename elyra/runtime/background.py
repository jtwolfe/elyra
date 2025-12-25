from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass
class BackgroundWorkerGroup:
    """Per-connection background workers for Phase 5.

    This is intentionally scoped to the websocket session so it's easy to cancel
    and doesn't require global braid discovery.
    """

    engine: any
    dream_interval_s: int
    metacog_interval_s: int

    def __post_init__(self) -> None:
        self._stop = asyncio.Event()
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self._tasks.append(asyncio.create_task(self._loop(self.dream_interval_s, self.engine.dream_tick, "dream")))
        self._tasks.append(
            asyncio.create_task(self._loop(self.metacog_interval_s, self.engine.metacog_tick, "metacog"))
        )

    async def stop(self) -> None:
        self._stop.set()
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except Exception:
                pass
        self._tasks = []

    async def _loop(self, interval_s: int, fn, name: str) -> None:
        interval_s = max(1, int(interval_s))
        while not self._stop.is_set():
            try:
                await asyncio.sleep(interval_s)
                fn()
            except asyncio.CancelledError:
                return
            except Exception:
                # Best-effort; engine will record any needed observation deltas itself.
                continue


