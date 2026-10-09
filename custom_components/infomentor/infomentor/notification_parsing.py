"""Validation for InfoMentor NotificationApp responses."""

from typing import Any


class NotificationFormatError(ValueError):
	"""The response cannot safely be interpreted as a notification list."""


def parse_notification_list(data: Any) -> tuple[list[dict[str, Any]], int]:
	"""Extract notification objects and count malformed rows.

	A timestamp-only GetNotifications heartbeat is intentionally rejected rather
	than misreported as a valid empty list. An explicitly empty notifications
	array, however, is a valid response.
	"""
	if isinstance(data, list):
		raw_items = data
	elif isinstance(data, dict) and isinstance(data.get("notifications"), list):
		raw_items = data["notifications"]
	else:
		raise NotificationFormatError("Unexpected InfoMentor notification response format")

	valid: list[dict[str, Any]] = []
	skipped = 0
	for item in raw_items:
		if not isinstance(item, dict):
			skipped += 1
			continue
		identifier = item.get("id")
		if isinstance(identifier, bool) or not (
			isinstance(identifier, int)
			or (isinstance(identifier, str) and identifier.isdigit())
		):
			skipped += 1
			continue
		if int(identifier) <= 0:
			skipped += 1
			continue
		valid.append(item)

	if raw_items and not valid:
		raise NotificationFormatError("No valid notifications in non-empty response")
	return valid, skipped
