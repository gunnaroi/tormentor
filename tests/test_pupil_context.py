"""Selected-pupil detection from the parent bootstrap."""

import importlib.util
import unittest
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "custom_components/infomentor/infomentor/pupil_context.py"
SPEC = importlib.util.spec_from_file_location("pupil_context", SOURCE)
pupil_context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pupil_context)


class PupilContextTests(unittest.TestCase):
	def test_finds_only_selected_child(self):
		html = '<script>IMHome.home.homeData = {"account":{"pupils":[{"id":"one","selected":false},{"id":"two","selected":true}]}}; IMHome.home.init();</script>'
		self.assertEqual(pupil_context.selected_pupil_id(html), "two")

	def test_ambiguous_selection_is_not_assumed(self):
		html = '<script>IMHome.home.homeData = {"account":{"pupils":[{"id":"one","selected":true},{"id":"two","selected":true}]}};</script>'
		self.assertIsNone(pupil_context.selected_pupil_id(html))


if __name__ == "__main__":
	unittest.main()
