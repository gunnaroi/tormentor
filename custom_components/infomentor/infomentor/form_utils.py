"""HTML form parsing helpers for InfoMentor authentication."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict


FORM_TAG_PATTERN = re.compile(r"<form\b[^>]*>.*?</form>", re.IGNORECASE | re.DOTALL)
INPUT_TAG_PATTERN = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
BUTTON_TAG_PATTERN = re.compile(r"<button\b[^>]*>.*?</button>", re.IGNORECASE | re.DOTALL)
SELECT_TAG_PATTERN = re.compile(r"<select\b[^>]*>.*?</select>", re.IGNORECASE | re.DOTALL)
TEXTAREA_TAG_PATTERN = re.compile(r"<textarea\b[^>]*>.*?</textarea>", re.IGNORECASE | re.DOTALL)
OPTION_TAG_PATTERN = re.compile(r"<option\b[^>]*>.*?</option>", re.IGNORECASE | re.DOTALL)

DEFAULT_FORM_METHOD = "post"

USERNAME_FIELD_HINTS = (
	"username",
	"user",
	"email",
	"e-mail",
	"mail",
	"login",
	"epost",
	"notandanafn",
	"txtnotandanafn",
)
PASSWORD_FIELD_HINTS = (
	"password",
	"pass",
	"pwd",
	"lykilord",
	"losenord",
	"txtlykilord",
	"lykilorð",
	"txtlykilorð",
)
SUBMIT_FIELD_HINTS = (
	"login",
	"logga",
	"sign",
	"submit",
	"authenticate",
	"next",
	"continue",
	"innskrá",
)

USERNAME_INPUT_TYPES = {"text", "email"}
PASSWORD_INPUT_TYPES = {"password"}
SUBMIT_INPUT_TYPES = {"submit", "image"}


@dataclass
class ParsedInput:
	name: str
	value: str
	input_type: str
	field_id: Optional[str]
	autocomplete: Optional[str]
	checked: bool
	disabled: bool
	raw_tag: str


@dataclass
class ParsedForm:
	action: Optional[str]
	method: str
	enctype: Optional[str]
	inputs: List[ParsedInput]
	selects: Dict[str, str]
	textareas: Dict[str, str]
	raw_html: str


def parse_forms(html_content: str) -> List[ParsedForm]:
	"""Parse all HTML forms in the content."""
	forms: List[ParsedForm] = []
	if not html_content:
		return forms

	for match in FORM_TAG_PATTERN.finditer(html_content):
		form_html = match.group(0)
		form_tag_match = re.search(r"<form\b[^>]*>", form_html, re.IGNORECASE)
		form_tag = form_tag_match.group(0) if form_tag_match else ""
		action = _extract_attr(form_tag, "action")
		method = (_extract_attr(form_tag, "method") or DEFAULT_FORM_METHOD).lower()
		enctype = _extract_attr(form_tag, "enctype")

		inputs = _parse_inputs(form_html)
		selects = _parse_selects(form_html)
		textareas = _parse_textareas(form_html)

		forms.append(
			ParsedForm(
				action=action,
				method=method,
				enctype=enctype,
				inputs=inputs,
				selects=selects,
				textareas=textareas,
				raw_html=form_html,
			)
		)

	return forms


def extract_hidden_fields(html_content: str) -> List[Tuple[str, str]]:
	"""Extract hidden input fields from HTML content."""
	hidden_fields: List[Tuple[str, str]] = []
	if not html_content:
		return hidden_fields

	for input_tag in INPUT_TAG_PATTERN.findall(html_content):
		input_type = (_extract_attr(input_tag, "type") or "text").lower()
		if input_type != "hidden":
			continue
		name = _extract_attr(input_tag, "name")
		if not name:
			continue
		value = _extract_attr(input_tag, "value") or ""
		hidden_fields.append((name, value))

	return hidden_fields


def select_login_form(forms: List[ParsedForm]) -> Optional[ParsedForm]:
	"""Select the most likely login form (password-based) from parsed forms."""
	if not forms:
		return None

	best_form: Optional[ParsedForm] = None
	best_score = -1

	for form in forms:
		score = _score_form(form)
		if score > best_score:
			best_score = score
			best_form = form

	if best_form and best_score > 0:
		return best_form

	return None


def build_login_form_data(
	form: ParsedForm,
	username: str,
	password: str,
) -> Tuple[List[Tuple[str, str]], Optional[str], Optional[str], Optional[str]]:
	"""Build form payload for username/password submission."""
	form_fields: List[Tuple[str, str]] = []

	for field in form.inputs:
		if field.disabled or not field.name:
			continue
		if field.input_type in SUBMIT_INPUT_TYPES:
			continue
		if field.input_type in {"checkbox", "radio"} and not field.checked:
			continue
		form_fields.append((field.name, field.value or ""))

	for name, value in form.selects.items():
		form_fields.append((name, value))

	for name, value in form.textareas.items():
		form_fields.append((name, value))

	username_field = _pick_best_field(form.inputs, USERNAME_INPUT_TYPES, USERNAME_FIELD_HINTS, "username")
	password_field = _pick_best_field(form.inputs, PASSWORD_INPUT_TYPES, PASSWORD_FIELD_HINTS, "current-password")
	submit_field = _pick_submit_field(form.inputs)

	if username_field:
		_replace_field(form_fields, username_field.name, username)
	if password_field:
		_replace_field(form_fields, password_field.name, password)
	if submit_field and submit_field.name:
		_replace_field(form_fields, submit_field.name, submit_field.value or "1")

	return (
		form_fields,
		username_field.name if username_field else None,
		password_field.name if password_field else None,
		submit_field.name if submit_field else None,
	)


def _parse_inputs(form_html: str) -> List[ParsedInput]:
	fields: List[ParsedInput] = []

	for input_tag in INPUT_TAG_PATTERN.findall(form_html):
		name = _extract_attr(input_tag, "name")
		if not name:
			continue
		input_type = (_extract_attr(input_tag, "type") or "text").lower()
		value = _extract_attr(input_tag, "value") or ""
		field_id = _extract_attr(input_tag, "id")
		autocomplete = _extract_attr(input_tag, "autocomplete")
		checked = _has_attribute(input_tag, "checked")
		disabled = _has_attribute(input_tag, "disabled")

		fields.append(
			ParsedInput(
				name=name,
				value=value,
				input_type=input_type,
				field_id=field_id,
				autocomplete=autocomplete,
				checked=checked,
				disabled=disabled,
				raw_tag=input_tag,
			)
		)

	for button_tag in BUTTON_TAG_PATTERN.findall(form_html):
		name = _extract_attr(button_tag, "name")
		if not name:
			continue
		input_type = (_extract_attr(button_tag, "type") or "submit").lower()
		value = _extract_attr(button_tag, "value")
		if value is None:
			value = _extract_inner_text(button_tag)
		field_id = _extract_attr(button_tag, "id")
		autocomplete = _extract_attr(button_tag, "autocomplete")
		checked = _has_attribute(button_tag, "checked")
		disabled = _has_attribute(button_tag, "disabled")

		fields.append(
			ParsedInput(
				name=name,
				value=value or "",
				input_type=input_type,
				field_id=field_id,
				autocomplete=autocomplete,
				checked=checked,
				disabled=disabled,
				raw_tag=button_tag,
			)
		)

	return fields


def _parse_selects(form_html: str) -> Dict[str, str]:
	selects: Dict[str, str] = {}

	for select_tag in SELECT_TAG_PATTERN.findall(form_html):
		name = _extract_attr(select_tag, "name")
		if not name:
			continue
		selected_value = _extract_selected_option(select_tag)
		if selected_value is not None:
			selects[name] = selected_value

	return selects


def _parse_textareas(form_html: str) -> Dict[str, str]:
	textareas: Dict[str, str] = {}

	for textarea_tag in TEXTAREA_TAG_PATTERN.findall(form_html):
		name = _extract_attr(textarea_tag, "name")
		if not name:
			continue
		value = _extract_textarea_value(textarea_tag)
		textareas[name] = value

	return textareas


def _extract_selected_option(select_html: str) -> Optional[str]:
	options = OPTION_TAG_PATTERN.findall(select_html)
	if not options:
		return None

	for option_tag in options:
		if _has_attribute(option_tag, "selected"):
			return _extract_option_value(option_tag)

	return _extract_option_value(options[0])


def _extract_option_value(option_tag: str) -> str:
	value = _extract_attr(option_tag, "value")
	if value is not None:
		return value
	return _extract_inner_text(option_tag)


def _extract_textarea_value(textarea_tag: str) -> str:
	match = re.search(r"<textarea\b[^>]*>(.*?)</textarea>", textarea_tag, re.IGNORECASE | re.DOTALL)
	if not match:
		return ""
	return html.unescape(match.group(1).strip())


def _extract_inner_text(tag_html: str) -> str:
	text = re.sub(r"<[^>]+>", "", tag_html)
	return html.unescape(text).strip()


def _extract_attr(tag_html: str, attr_name: str) -> Optional[str]:
	pattern = rf'{attr_name}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))'
	match = re.search(pattern, tag_html, re.IGNORECASE)
	if not match:
		return None
	value = match.group(1) or match.group(2) or match.group(3) or ""
	return html.unescape(value.strip())


def _has_attribute(tag_html: str, attr_name: str) -> bool:
	return bool(re.search(rf"\b{re.escape(attr_name)}\b", tag_html, re.IGNORECASE))


def _score_form(form: ParsedForm) -> int:
	has_password = any(field.input_type in PASSWORD_INPUT_TYPES for field in form.inputs)
	has_username = any(
		field.input_type in USERNAME_INPUT_TYPES or _field_matches_hints(field, USERNAME_FIELD_HINTS)
		for field in form.inputs
	)

	if not has_password:
		return 0

	score = 1000
	if has_username:
		score += 200

	action_lower = (form.action or "").lower()
	if "login" in action_lower or "authentication" in action_lower:
		score += 50

	if any(_field_matches_hints(field, SUBMIT_FIELD_HINTS) for field in form.inputs):
		score += 20

	return score


def _pick_best_field(
	inputs: List[ParsedInput],
	allowed_types: set,
	hints: Tuple[str, ...],
	autocomplete_hint: str,
) -> Optional[ParsedInput]:
	best_field = None
	best_score = -1

	for field in inputs:
		if field.disabled:
			continue
		if field.input_type not in allowed_types:
			continue
		score = 0
		if field.autocomplete and autocomplete_hint in field.autocomplete.lower():
			score += 100
		if _field_matches_hints(field, hints):
			score += 60
		if field.input_type == "email":
			score += 10
		if score > best_score:
			best_score = score
			best_field = field

	if best_field and best_score > 0:
		return best_field

	if inputs:
		for field in inputs:
			if field.input_type in allowed_types:
				return field

	return None


def _pick_submit_field(inputs: List[ParsedInput]) -> Optional[ParsedInput]:
	best_field = None
	best_score = -1

	for field in inputs:
		if field.disabled:
			continue
		if field.input_type not in SUBMIT_INPUT_TYPES and field.input_type != "submit":
			continue
		score = 0
		if _field_matches_hints(field, SUBMIT_FIELD_HINTS):
			score += 50
		if score > best_score:
			best_score = score
			best_field = field

	if best_field:
		return best_field

	for field in inputs:
		if field.input_type in SUBMIT_INPUT_TYPES or field.input_type == "submit":
			return field

	return None


def _field_matches_hints(field: ParsedInput, hints: Tuple[str, ...]) -> bool:
	name_lower = (field.name or "").lower()
	id_lower = (field.field_id or "").lower()

	return any(hint in name_lower or hint in id_lower for hint in hints)


def _replace_field(form_fields: List[Tuple[str, str]], field_name: str, value: str) -> None:
	replaced = False
	for idx, (name, _) in enumerate(form_fields):
		if name == field_name:
			form_fields[idx] = (field_name, value)
			replaced = True

	if not replaced:
		form_fields.append((field_name, value))
