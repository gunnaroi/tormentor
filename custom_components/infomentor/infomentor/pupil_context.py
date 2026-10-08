"""Read the selected pupil from the InfoMentor parent page without executing scripts."""

import json
import re


def selected_pupil_id(html: str) -> str | None:
	"""Return the unique selected pupil ID, or None if the page cannot prove it."""
	match = re.search(r"IMHome\.home\.homeData\s*=\s*", html)
	if not match:
		return None
	try:
		data, _ = json.JSONDecoder().raw_decode(html[match.end():].lstrip())
		pupils = data["account"]["pupils"]
		selected = [str(pupil["id"]) for pupil in pupils if pupil.get("selected") is True]
		return selected[0] if len(selected) == 1 else None
	except (ValueError, TypeError, KeyError, AttributeError):
		return None
