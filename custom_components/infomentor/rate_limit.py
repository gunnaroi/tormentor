"""Per-account request pacing and server-directed cooldowns."""
import asyncio
import time
from contextlib import AsyncExitStack, asynccontextmanager
from email.utils import parsedate_to_datetime


def retry_delay(value, now=None):
    """Accept Retry-After seconds or HTTP dates; default to one hour."""
    now = time.time() if now is None else now
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - now
        except (TypeError, ValueError, OverflowError):
            return 3600
    if not (0 <= seconds < float("inf")):
        return 3600
    return max(60, seconds)


class RateLimitedSession:
    """Wrap only this integration's session access, never mutate HA's session."""

    def __init__(self, session, clock=time.monotonic, sleep=asyncio.sleep):
        self._session = session
        self._clock = clock
        self._sleep = sleep
        self._blocked_until = 0
        self._next_request = 0
        self._lock = asyncio.Lock()

    @property
    def cooldown_remaining(self):
        return max(0, self._blocked_until - self._clock())

    def __getattr__(self, name):
        return getattr(self._session, name)

    @asynccontextmanager
    async def request(self, method, url, **kwargs):
        async with AsyncExitStack() as stack:
            async with self._lock:
                if self.cooldown_remaining:
                    raise RuntimeError("InfoMentor server cooldown active; request skipped")
                await self._sleep(max(0, self._next_request - self._clock()))
                self._next_request = self._clock() + 1
                response = await stack.enter_async_context(self._session.request(method, url, **kwargs))
                if response.status == 429 or (response.status == 503 and response.headers.get("Retry-After")):
                    self._blocked_until = self._clock() + retry_delay(response.headers.get("Retry-After"))
                    raise RuntimeError("InfoMentor requested a cooldown; further requests suspended")
            # Authentication can make nested requests while reading a response.
            yield response

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)
