#!/usr/bin/env python3
"""Unit tests for login form parsing helpers."""

from pathlib import Path
import importlib.util


BASE_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = BASE_DIR / "custom_components" / "infomentor" / "infomentor"


spec = importlib.util.spec_from_file_location("form_utils", LIB_DIR / "form_utils.py")
form_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(form_utils)


parse_forms = form_utils.parse_forms
select_login_form = form_utils.select_login_form
build_login_form_data = form_utils.build_login_form_data
extract_hidden_fields = form_utils.extract_hidden_fields


def test_selects_login_form_and_builds_payload():
	"""Ensure the login form is selected and payload includes all fields."""
	html = """
	<html>
		<body>
			<form id="openid_message" action="https://example.com/openid" method="post">
				<input type="hidden" name="oauth_token" value="abc123" />
			</form>
			<form action="/swedish/production/mentor/default.aspx" method="post">
				<input type="hidden" name="__VIEWSTATE" value="state" />
				<input type="text" name="login_ascx$txtNotandanafn" />
				<input type="password" name="login_ascx$txtLykilord" />
				<input type="checkbox" name="remember" value="1" checked />
				<select name="login_ascx$ddlIdpType">
					<option value="im">InfoMentor</option>
				</select>
				<button type="submit" name="login_ascx$btnLogin">Logga in</button>
			</form>
		</body>
	</html>
	"""

	forms = parse_forms(html)
	assert len(forms) == 2

	login_form = select_login_form(forms)
	assert login_form is not None

	fields, username_field, password_field, submit_field = build_login_form_data(
		login_form,
		"user@example.com",
		"password123",
	)

	field_names = [name for name, _ in fields]
	assert "__VIEWSTATE" in field_names
	assert "login_ascx$ddlIdpType" in field_names
	assert ("remember", "1") in fields
	assert username_field == "login_ascx$txtNotandanafn"
	assert password_field == "login_ascx$txtLykilord"
	assert submit_field == "login_ascx$btnLogin"


def test_uses_selected_option_when_present():
	"""Ensure selected option is preferred when present."""
	html = """
	<form action="/login" method="post">
		<input type="text" name="username" />
		<input type="password" name="password" />
		<select name="region">
			<option value="eu">EU</option>
			<option value="se" selected>Sweden</option>
		</select>
		<input type="submit" name="submit" value="Login" />
	</form>
	"""

	forms = parse_forms(html)
	login_form = select_login_form(forms)
	assert login_form is not None

	fields, _, _, _ = build_login_form_data(login_form, "user", "pass")
	assert ("region", "se") in fields


def test_extract_hidden_fields_captures_viewstate_and_idp_fields():
	"""Hidden field extraction should include viewstate and IdP list entries."""
	html = """
	<form action="./" method="post">
		<input type="hidden" name="__VIEWSTATE" value="state" />
		<input type="hidden" name="__EVENTVALIDATION" value="validation" />
		<input type="hidden" name="login_ascx$IdpListRepeater$ctl00$url" value="https://sso.infomentor.se/login.ashx?idp=test" />
		<input type="hidden" name="login_ascx$IdpListRepeater$ctl00$number" value="98" />
	</form>
	"""

	hidden_fields = extract_hidden_fields(html)
	assert ("__VIEWSTATE", "state") in hidden_fields
	assert ("__EVENTVALIDATION", "validation") in hidden_fields
	assert any(name.endswith("$url") for name, _ in hidden_fields)

