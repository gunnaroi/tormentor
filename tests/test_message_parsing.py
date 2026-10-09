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


class NotificationParsingTests(unittest.TestCase):
	def setUp(self):
		path = SOURCE.with_name("notification_parsing.py")
		spec = importlib.util.spec_from_file_location("notification_parsing", path)
		self.parser = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(self.parser)

	def test_extracts_app_data_notification_list(self):
		items, skipped = self.parser.parse_notification_list({
			"timestamp": "2026-10-09 21:47:18.601",
			"notifications": [{"id": 7, "title": "New", "state": "New"}],
		})
		self.assertEqual(len(items), 1)
		self.assertEqual(skipped, 0)

	def test_timestamp_heartbeat_is_not_an_empty_list(self):
		with self.assertRaises(self.parser.NotificationFormatError):
			self.parser.parse_notification_list({"timestamp": "2026-10-09 21:44:00.405"})

	def test_explicit_empty_notifications_is_valid(self):
		self.assertEqual(
			self.parser.parse_notification_list({"notifications": []}),
			([], 0),
		)

	def test_malformed_rows_are_skipped_but_not_silently_all_dropped(self):
		items, skipped = self.parser.parse_notification_list({"notifications": [{"id": 5}, {"title": "missing id"}]})
		self.assertEqual((len(items), skipped), (1, 1))
		with self.assertRaises(self.parser.NotificationFormatError):
			self.parser.parse_notification_list({"notifications": [{"title": "invalid"}]})
