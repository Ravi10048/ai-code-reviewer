from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Token-bucket rate limiter for LLM API calls."""

    max_requests: int = 30
    window_seconds: float = 60.0
    _timestamps: list[float] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        async with self._lock:
            now = time.monotonic()
            # Remove timestamps outside the window
            self._timestamps = [
                t for t in self._timestamps if now - t < self.window_seconds
            ]

            if len(self._timestamps) >= self.max_requests:
                oldest = self._timestamps[0]
                wait_time = self.window_seconds - (now - oldest)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Clean up again after sleeping
                    now = time.monotonic()
                    self._timestamps = [
                        t for t in self._timestamps if now - t < self.window_seconds
                    ]

            self._timestamps.append(time.monotonic())

    @property
    def available_slots(self) -> int:
        now = time.monotonic()
        active = [t for t in self._timestamps if now - t < self.window_seconds]
        return max(0, self.max_requests - len(active))
