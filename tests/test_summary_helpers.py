"""Tests for dashboard/Assist/MCP summary helpers."""

import unittest
from datetime import date, datetime, time
import importlib.util
from pathlib import Path
from types import SimpleNamespace

SUMMARY_PATH = Path(__file__).parents[1] / "custom_components" / "infomentor" / "summary.py"
SPEC = importlib.util.spec_from_file_location("infomentor_summary", SUMMARY_PATH)
summary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(summary)

entry_summary = summary.entry_summary
is_homework = summary.is_homework
schedule_day_summary = summary.schedule_day_summary
state_text = summary.state_text
week_summary = summary.week_summary


class SummaryHelperTests(unittest.TestCase):
	def test_state_is_limited_to_home_assistant_maximum(self):
		self.assertEqual(255, len(state_text("x" * 300)))

	def test_homework_matches_english_and_icelandic(self):
		self.assertTrue(is_homework(SimpleNamespace(entry_type="assignment", title="Math")))
		self.assertTrue(is_homework(SimpleNamespace(entry_type="", title="Heimanám")))
		self.assertFalse(is_homework(SimpleNamespace(entry_type="announcement", title="Trip")))

	def test_entry_summary_includes_title_and_content(self):
		entry = SimpleNamespace(title="Reading", content="Read chapter 2")
		self.assertEqual("Reading: Read chapter 2", entry_summary([entry], 1))

	def test_day_summary_includes_time_and_subject(self):
		entry = SimpleNamespace(
			subject="Mathematics", title="Math", start_time=time(9), end_time=time(9, 40)
		)
		day = SimpleNamespace(timetable_entries=[entry], time_registrations=[])
		self.assertEqual("09:00-09:40 Mathematics", schedule_day_summary(day))

	def test_week_is_sunday_through_saturday(self):
		def day(day_number):
			return SimpleNamespace(
				date=datetime(2026, 8, day_number),
				timetable_entries=[],
				time_registrations=[],
			)

		result = week_summary([day(22), day(23), day(29), day(30)], date(2026, 8, 26))
		self.assertNotIn("Sat 22 Aug", result)
		self.assertIn("Sun 23 Aug", result)
		self.assertIn("Sat 29 Aug", result)
		self.assertNotIn("Sun 30 Aug", result)


if __name__ == "__main__":
	unittest.main()
