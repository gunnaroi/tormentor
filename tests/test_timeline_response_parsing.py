"""Timeline response variants and privacy-safe diagnostics."""

from custom_components.infomentor.infomentor.client import InfoMentorClient


def test_finds_pascal_case_entries_inside_result_wrapper():
	payload = {
		"Result": {
			"TimelineEntries": [
				{
					"Id": 42,
					"Title": "Heimanám",
					"Description": "Lesa kafla",
					"Date": "2026-08-31T12:00:00",
					"Type": "Homework",
				}
			]
		}
	}

	entries = InfoMentorClient()._parse_timeline_data(payload, "child-1")

	assert len(entries) == 1
	assert entries[0].id == "42"
	assert entries[0].title == "Heimanám"
	assert entries[0].content == "Lesa kafla"
	assert entries[0].entry_type == "Homework"


def test_shape_diagnostics_do_not_contain_scalar_content():
	payload = {
		"Result": {
			"TimelineEntries": [
				{"Title": "private title", "Description": "private body"}
			]
		}
	}

	shape = InfoMentorClient._describe_json_shape(payload)
	serialized = repr(shape)

	assert "TimelineEntries" in serialized
	assert "private title" not in serialized
	assert "private body" not in serialized
	assert shape["children"]["Result"]["children"]["TimelineEntries"]["count"] == 1
