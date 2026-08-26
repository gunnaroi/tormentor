"""Tests for dashboard/Assist/MCP summaries."""

import importlib.util
import unittest
from datetime import datetime, time
from pathlib import Path
from types import SimpleNamespace

SUMMARY_PATH = Path(__file__).parents[1] / "custom_components" / "infomentor" / "summary.py"
SPEC = importlib.util.spec_from_file_location("infomentor_summary", SUMMARY_PATH)
summary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(summary)


class SummaryHelperTests(unittest.TestCase):
	def test_latest_content_contains_title_and_content(self):
		entry = SimpleNamespace(title="Reading", content="Read chapter 2")
		self.assertEqual("Reading: Read chapter 2", summary.content_summary(entry, "None"))

	def test_state_is_limited_to_home_assistant_maximum(self):
		self.assertEqual(255, len(summary.limited("x" * 300)))

	def test_next_class_ignores_classes_that_started(self):
		past = SimpleNamespace(date=datetime(2026, 8, 26), start_time=time(8))
		future = SimpleNamespace(date=datetime(2026, 8, 26), start_time=time(10))
		day = SimpleNamespace(timetable_entries=[past, future])
		self.assertIs(future, summary.find_next_class([day], datetime(2026, 8, 26, 9)))

	def test_today_summary_contains_times_and_subjects(self):
		entry = SimpleNamespace(
			subject="Math", title="Mathematics", start_time=time(9), end_time=time(9, 40)
		)
		day = SimpleNamespace(timetable_entries=[entry], time_registrations=[])
		self.assertEqual("09:00-09:40 Math", summary.today_summary(day))


if __name__ == "__main__":
	unittest.main()
