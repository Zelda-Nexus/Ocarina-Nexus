"""
Generic delay-based rate limiter, generalizing the `time.sleep(SCRAPING_DELAY)`
pattern already used in `utils/wiki_api.py`. Tracks the last call's timestamp so
back-to-back calls sleep only for what's left of the interval, instead of
always sleeping the full delay regardless of how long the request itself took.
"""

import time


class RateLimiter:
    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds
        self._last_call: float | None = None

    def wait(self) -> None:
        if self._last_call is not None:
            elapsed = time.monotonic() - self._last_call
            remaining = self.delay_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call = time.monotonic()
