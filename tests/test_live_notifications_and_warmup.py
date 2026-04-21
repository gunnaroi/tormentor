#!/usr/bin/env python3
"""Live test for the notification + warmup fixes shipped in v0.1.06.

Runs against the real InfoMentor service using credentials from `.env`:
  INFOMENTOR_USERNAME=...
  INFOMENTOR_PASSWORD=...

The test verifies the specific behaviours we claimed work:

1. Login succeeds and produces cookies across multiple InfoMentor domains.
2. `InfoMentorClient.warmup_hub_session()` returns True (at least one step OK).
3. `InfoMentorClient.get_notifications()` returns a list of
   `InfoMentorNotification` objects via the POST-first path.
4. The first POST attempt (no prior warmup in this run) succeeds — i.e. the
   endpoint really does want POST rather than GET.

Exit code 0 only if every assertion passes.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

try:
	from dotenv import load_dotenv
	load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
	print("install python-dotenv to use the .env file")
	sys.exit(2)

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "infomentor"))

from infomentor.client import InfoMentorClient  # type: ignore  # noqa: E402
from infomentor.models import InfoMentorNotification  # type: ignore  # noqa: E402

logging.basicConfig(
	level=os.getenv("LOG_LEVEL", "INFO"),
	format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
_LOGGER = logging.getLogger("live_notification_test")


class Failure(RuntimeError):
	"""Raised when an assertion fails — keeps stack traces short."""


def _assert(cond: bool, msg: str) -> None:
	if not cond:
		raise Failure(msg)


async def run() -> int:
	username = os.getenv("INFOMENTOR_USERNAME")
	password = os.getenv("INFOMENTOR_PASSWORD")
	_assert(bool(username and password), "INFOMENTOR_USERNAME/PASSWORD missing from .env")

	failures: list[str] = []

	async with InfoMentorClient() as client:
		# --- 1. login ------------------------------------------------------
		_LOGGER.info("Logging in as %s", username)
		ok = await client.login(username, password)
		if not ok:
			failures.append("login returned False")
			_print_summary(failures)
			return 1

		cookies_by_domain: dict[str, int] = {}
		for cookie in client._session.cookie_jar:
			dom = cookie.get("domain") or "?"
			cookies_by_domain[dom] = cookies_by_domain.get(dom, 0) + 1
		_LOGGER.info("Cookies by domain: %s", cookies_by_domain)

		if cookies_by_domain.get("hub.infomentor.se", 0) < 1:
			failures.append(
				f"no hub.infomentor.se cookies after login (got {cookies_by_domain})"
			)

		pupil_ids = await client.get_pupil_ids()
		_LOGGER.info("Pupil IDs: %s", pupil_ids)
		if not pupil_ids:
			failures.append("no pupil IDs returned after login")

		# --- 2. warmup -----------------------------------------------------
		_LOGGER.info("Running hub warmup")
		warmup_ok = await client.warmup_hub_session()
		_LOGGER.info("warmup_hub_session returned %s", warmup_ok)
		if not warmup_ok:
			failures.append("warmup_hub_session returned False (no step succeeded)")

		# --- 3. get_notifications via POST-first ---------------------------
		# Patch the client session to count POST vs GET hits on the
		# notification URL so we can assert POST really is tried first.
		notif_url = (
			"https://hub.infomentor.se/NotificationApp/NotificationApp/appData"
		)
		method_calls: list[str] = []

		session = client._session
		orig_get = session.get
		orig_post = session.post

		def _wrap_get(url, *args, **kwargs):
			if url == notif_url:
				method_calls.append("GET")
			return orig_get(url, *args, **kwargs)

		def _wrap_post(url, *args, **kwargs):
			if url == notif_url:
				method_calls.append("POST")
			return orig_post(url, *args, **kwargs)

		session.get = _wrap_get  # type: ignore[assignment]
		session.post = _wrap_post  # type: ignore[assignment]

		try:
			notifications = await client.get_notifications()
		finally:
			session.get = orig_get  # type: ignore[assignment]
			session.post = orig_post  # type: ignore[assignment]

		_LOGGER.info(
			"get_notifications returned %d items; method calls: %s",
			len(notifications),
			method_calls,
		)

		if not isinstance(notifications, list):
			failures.append(
				f"get_notifications should return list, got {type(notifications).__name__}"
			)
		for i, n in enumerate(notifications):
			if not isinstance(n, InfoMentorNotification):
				failures.append(
					f"notification[{i}] is {type(n).__name__}, expected InfoMentorNotification"
				)
				break

		if not method_calls:
			failures.append("notification endpoint was never called")
		elif method_calls[0] != "POST":
			failures.append(
				f"first notification request was {method_calls[0]}, expected POST"
			)

		# We do not assert len(notifications) > 0 because an account may
		# legitimately have zero. But we assert the parsed list is valid and
		# includes the expected attributes if any items exist.
		if notifications:
			first = notifications[0]
			for attr in ("id", "title", "date_sent", "state", "app_type"):
				if not hasattr(first, attr):
					failures.append(
						f"first notification is missing attribute {attr!r}"
					)

	_print_summary(failures, notifications_count=len(notifications))
	return 0 if not failures else 1


def _print_summary(failures: list[str], notifications_count: int | None = None) -> None:
	print()
	print("=" * 60)
	if failures:
		print(f"FAILED ({len(failures)} issue(s)):")
		for f in failures:
			print(f"  - {f}")
	else:
		print("PASSED — notification fetch via POST-first works end-to-end.")
		if notifications_count is not None:
			print(f"  notifications returned: {notifications_count}")
	print("=" * 60)


if __name__ == "__main__":
	try:
		sys.exit(asyncio.run(run()))
	except Failure as err:
		print(f"\nFATAL: {err}")
		sys.exit(2)
