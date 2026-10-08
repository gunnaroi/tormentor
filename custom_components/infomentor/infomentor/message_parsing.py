"""Parsing for InfoMentor's paged direct-message API."""

from datetime import datetime, timezone
from typing import Any


class MessageFormatError(ValueError):
	"""The response cannot safely be interpreted as a message list."""


def parse_message_date(value: Any) -> datetime:
	"""Keep upstream dates; never replace a missing date with the current time."""
	if not isinstance(value, str) or not value:
		raise MessageFormatError("Missing message timestamp")
	try:
		parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
		return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
	except ValueError as err:
		try:
			return datetime.strptime(value, "%d.%m.%Y %H:%M")
		except ValueError:
			raise MessageFormatError("Invalid message timestamp") from err


def parse_message_list(data: Any) -> tuple[list[dict[str, Any]], int]:
	"""Return valid normalized rows and the number of malformed rows."""
	if not isinstance(data, dict) or not isinstance(data.get("items"), list):
		raise MessageFormatError("Unexpected message list format")
	result = []
	skipped = 0
	for item in data["items"]:
		try:
			if not isinstance(item, dict) or not isinstance(item.get("id"), int) or item["id"] <= 0:
				raise MessageFormatError("Invalid message ID")
			sender = item.get("sentUser")
			result.append({
				"id": str(item["id"]),
				"subject": str(item.get("messageSubject") or ""),
				"date": parse_message_date(item.get("timeSent")),
				"sender": sender.get("displayName") if isinstance(sender, dict) else None,
				"unread": bool(item.get("isNew", False)),
			})
		except MessageFormatError:
			skipped += 1
	if data["items"] and not result:
		raise MessageFormatError("No valid messages in non-empty response")
	return result, skipped
