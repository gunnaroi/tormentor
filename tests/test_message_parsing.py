"""Regression checks for the Icelandic direct-message response."""

import importlib.util
import unittest
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "custom_components/infomentor/infomentor/message_parsing.py"
SPEC = importlib.util.spec_from_file_location("message_parsing", SOURCE)
message_parsing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(message_parsing)


class MessageParsingTests(unittest.TestCase):
	def test_normalizes_real_response_fields(self):
		rows, skipped = message_parsing.parse_message_list({"items": [
			{"id": 12, "messageSubject": "Lunch", "timeSent": "2026-09-02T10:00:00", "sentUser": {"displayName": "School"}, "isNew": True},
		]})
		self.assertEqual(skipped, 0)
		self.assertEqual(rows[0]["subject"], "Lunch")
		self.assertEqual(rows[0]["sender"], "School")
		self.assertTrue(rows[0]["unread"])

	def test_unknown_wrapper_is_not_empty_inbox(self):
		with self.assertRaises(message_parsing.MessageFormatError):
			message_parsing.parse_message_list({"unexpected": []})

	def test_icelandic_message_timestamp(self):
		rows, skipped = message_parsing.parse_message_list({"items": [
			{"id": 41, "messageSubject": "Skólaferð", "timeSent": "11.09.2026 09:00"},
		]})
		self.assertEqual(skipped, 0)
		self.assertEqual(rows[0]["date"].isoformat(), "2026-09-11T09:00:00")

	def test_skips_bad_rows_without_erasing_valid_ones(self):
		rows, skipped = message_parsing.parse_message_list({"items": [
			{"id": 1, "messageSubject": "Valid", "timeSent": "2026-09-02T10:00:00"},
			{"id": 2, "timeSent": "invalid"},
		]})
		self.assertEqual((len(rows), skipped), (1, 1))


if __name__ == "__main__":
	unittest.main()
