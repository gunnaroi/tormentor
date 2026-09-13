import importlib.util
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("rate_limit", Path(__file__).parents[1] / "custom_components/infomentor/rate_limit.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RateLimitTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_after(self):
        self.assertEqual(module.retry_delay("120"), 120)
        self.assertEqual(module.retry_delay(None), 3600)
        self.assertEqual(module.retry_delay("bad"), 3600)
        self.assertEqual(module.retry_delay("Thu, 01 Jan 1970 00:02:00 GMT", 0), 120)
        self.assertEqual(module.retry_delay("nan"), 3600)

    async def test_cooldown_blocks_fallback_and_releases_response(self):
        for status in (429, 503):
            now = [100.0]
            calls, released = [], []
            @asynccontextmanager
            async def request(method, url, **kwargs):
                calls.append(method)
                try:
                    yield SimpleNamespace(status=status if len(calls) == 1 else 200, headers={"Retry-After": "120"})
                finally:
                    released.append(True)
            async def sleep(seconds):
                now[0] += seconds
            session = module.RateLimitedSession(SimpleNamespace(request=request), clock=lambda: now[0], sleep=sleep)
            with self.assertRaises(RuntimeError):
                async with session.get("https://example.invalid"):
                    self.fail("rate-limited response exposed")
            with self.assertRaises(RuntimeError):
                async with session.post("https://example.invalid/fallback"):
                    self.fail("fallback sent")
            self.assertEqual(calls, ["GET"])
            self.assertEqual(len(released), 1)
            now[0] += 120
            async with session.get("https://example.invalid") as response:
                self.assertEqual(response.status, 200)
            async with session.get("https://example.invalid"):
                pass
            self.assertEqual(now[0], 221)
            async with session.get("https://example.invalid/outer"):
                async with session.get("https://example.invalid/inner"):
                    pass
            self.assertEqual(now[0], 223)


if __name__ == "__main__":
    unittest.main()
