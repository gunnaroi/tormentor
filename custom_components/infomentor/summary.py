"""Compact summaries intended for dashboards, Assist, and MCP."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Iterable

MAX_STATE_LENGTH = 255


def compact(value: Any) -> str:
	"""Collapse whitespace in upstream text."""
	return " ".join(str(value or "").split())


def limited(value: str, empty: str = "No data") -> str:
	"""Fit text within Home Assistant's maximum state length."""
	value = compact(value) or empty
	if len(value) <= MAX_STATE_LENGTH:
		return value
	return value[: MAX_STATE_LENGTH - 1].rstrip() + "…"


def content_summary(entry: Any | None, empty: str) -> str:
	"""Return the title and content of one news/timeline entry."""
	if entry is None:
		return empty
	title = compact(getattr(entry, "title", "")) or "Untitled"
	content = compact(
		getattr(entry, "content", getattr(entry, "description", ""))
	)
	return limited(f"{title}: {content}" if content else title, empty)


def find_next_class(days: Iterable[Any], now: datetime) -> Any | None:
	"""Find the next timetable entry at or after the supplied local time."""
	candidates = []
	for day in days:
		for entry in getattr(day, "timetable_entries", []):
			entry_date = entry.date.date()
			entry_time = entry.start_time or time.min
			starts_at = datetime.combine(entry_date, entry_time)
			if starts_at >= now:
				candidates.append((starts_at, entry))
	return min(candidates, key=lambda item: item[0])[1] if candidates else None


def class_summary(entry: Any | None) -> str:
	"""Return a readable summary of one class."""
	if entry is None:
		return "No upcoming class"
	title = compact(getattr(entry, "subject", "") or getattr(entry, "title", "")) or "Class"
	day = entry.date.strftime("%a %d %b")
	if entry.start_time and entry.end_time:
		return limited(
			f"{day}, {entry.start_time.strftime('%H:%M')}-{entry.end_time.strftime('%H:%M')}: {title}"
		)
	return limited(f"{day}: {title}")


def today_summary(day: Any | None) -> str:
	"""Return a readable summary of today's timetable and registrations."""
	if day is None:
		return "No schedule data"
	items = []
	for entry in getattr(day, "timetable_entries", []):
		title = compact(getattr(entry, "subject", "") or getattr(entry, "title", "")) or "Class"
		if entry.start_time and entry.end_time:
			items.append(
				f"{entry.start_time.strftime('%H:%M')}-{entry.end_time.strftime('%H:%M')} {title}"
			)
		else:
			items.append(title)
	for registration in getattr(day, "time_registrations", []):
		title = compact(getattr(registration, "type", "")) or "Registration"
		if registration.start_time and registration.end_time:
			items.append(
				f"{registration.start_time.strftime('%H:%M')}-{registration.end_time.strftime('%H:%M')} {title}"
			)
		else:
			items.append(title)
	return limited(", ".join(items), "No classes today")
