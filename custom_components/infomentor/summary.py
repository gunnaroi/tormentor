"""Plain-text summaries for dashboards, Assist, and MCP clients."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Sequence

MAX_STATE_LENGTH = 255


def compact_text(value: Any) -> str:
	"""Collapse whitespace in text returned by InfoMentor."""
	return " ".join(str(value or "").split())


def state_text(value: str, empty: str = "No entries") -> str:
	"""Return a useful value that fits Home Assistant's state limit."""
	value = compact_text(value) or empty
	if len(value) <= MAX_STATE_LENGTH:
		return value
	return value[: MAX_STATE_LENGTH - 1].rstrip() + "…"


def is_homework(entry: Any) -> bool:
	"""Identify homework/assignment timeline entries."""
	haystack = " ".join(
		compact_text(value).casefold()
		for value in (
			getattr(entry, "entry_type", ""),
			getattr(entry, "title", ""),
		)
	)
	return any(
		marker in haystack
		for marker in ("assignment", "homework", "heimanám", "heimaverkefni")
	)


def entry_summary(entries: Iterable[Any], limit: int) -> str:
	"""Summarise timeline or news entries, newest first."""
	parts = []
	for entry in list(entries)[:limit]:
		title = compact_text(getattr(entry, "title", "")) or "Untitled"
		content = compact_text(
			getattr(entry, "content", getattr(entry, "description", ""))
		)
		parts.append(f"{title}: {content}" if content else title)
	return state_text(" | ".join(parts))


def schedule_day_summary(day: Any | None, label: str | None = None) -> str:
	"""Summarise one schedule day."""
	if day is None:
		return state_text(f"{label}: No schedule data" if label else "No schedule data")

	items = []
	for entry in getattr(day, "timetable_entries", []):
		title = compact_text(
			getattr(entry, "subject", "") or getattr(entry, "title", "")
		) or "Class"
		start = getattr(entry, "start_time", None)
		end = getattr(entry, "end_time", None)
		times = (
			f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')} "
			if start and end
			else ""
		)
		items.append(f"{times}{title}")

	for registration in getattr(day, "time_registrations", []):
		kind = compact_text(getattr(registration, "type", "")) or "Registration"
		start = getattr(registration, "start_time", None)
		end = getattr(registration, "end_time", None)
		times = (
			f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')} "
			if start and end
			else ""
		)
		items.append(f"{times}{kind}")

	prefix = f"{label}: " if label else ""
	return state_text(prefix + (", ".join(items) if items else "No classes"))


def week_summary(days: Sequence[Any], today: date) -> str:
	"""Summarise the current Sunday-through-Saturday calendar week."""
	days_since_sunday = (today.weekday() + 1) % 7
	week_start = today.fromordinal(today.toordinal() - days_since_sunday)
	week_end = today.fromordinal(week_start.toordinal() + 6)
	selected = sorted(
		(day for day in days if week_start <= day.date.date() <= week_end),
		key=lambda day: day.date,
	)
	parts = [
		schedule_day_summary(day, day.date.strftime("%a %d %b"))
		for day in selected
	]
	return state_text(" | ".join(parts), "No schedule data")
