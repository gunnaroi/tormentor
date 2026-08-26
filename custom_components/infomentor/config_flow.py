"""Config flow for InfoMentor integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .infomentor.exceptions import InfoMentorAuthError, InfoMentorConnectionError

from .const import DOMAIN, CONF_NOTIFY_SERVICES

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
	{
		vol.Required(CONF_USERNAME): str,
		vol.Required(CONF_PASSWORD): str,
	}
)


class InfoMentorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
	"""Handle a config flow for InfoMentor."""
	
	VERSION = 1

	@staticmethod
	@callback
	def async_get_options_flow(
		config_entry: config_entries.ConfigEntry,
	) -> config_entries.OptionsFlow:
		"""Create the options flow."""
		return InfoMentorOptionsFlow()
	
	async def async_step_user(
		self, user_input: Optional[Dict[str, Any]] = None
	) -> FlowResult:
		"""Handle the initial step."""
		errors: Dict[str, str] = {}
		
		if user_input is not None:
			# Validate the user input
			try:
				await self._test_credentials(
					user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
				)
			except InfoMentorAuthError:
				errors["base"] = "invalid_auth"
			except InfoMentorConnectionError:
				errors["base"] = "cannot_connect"
			except Exception:  # pylint: disable=broad-except
				_LOGGER.exception("Unexpected exception")
				errors["base"] = "unknown"
			else:
				# Create the entry
				await self.async_set_unique_id(user_input[CONF_USERNAME])
				self._abort_if_unique_id_configured()
				
				return self.async_create_entry(
					title=f"InfoMentor ({user_input[CONF_USERNAME]})",
					data=user_input,
				)
		
		return self.async_show_form(
			step_id="user",
			data_schema=STEP_USER_DATA_SCHEMA,
			errors=errors,
		)
	
	async def async_step_reauth(
		self, entry_data: Dict[str, Any]
	) -> FlowResult:
		"""Start re-authentication for an existing entry."""
		return await self.async_step_reauth_confirm()

	async def async_step_reauth_confirm(
		self, user_input: Optional[Dict[str, Any]] = None
	) -> FlowResult:
		"""Validate replacement credentials and update the existing entry."""
		errors: Dict[str, str] = {}
		reauth_entry = self._get_reauth_entry()
		
		if user_input is not None:
			try:
				# Test the new credentials
				await self._test_credentials(
					user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
				)
			except InfoMentorAuthError:
				errors["base"] = "invalid_auth"
			except InfoMentorConnectionError:
				errors["base"] = "cannot_connect"
			except Exception:  # pylint: disable=broad-except
				_LOGGER.exception("Unexpected exception during reauth")
				errors["base"] = "unknown"
			else:
				await self.async_set_unique_id(user_input[CONF_USERNAME])
				self._abort_if_unique_id_mismatch(reason="wrong_account")
				return self.async_update_reload_and_abort(
					reauth_entry,
					data_updates=user_input,
				)
		
		# Show the reauth form with current username pre-filled if available
		current_username = reauth_entry.data.get(CONF_USERNAME, "")
		
		schema = vol.Schema({
			vol.Required(CONF_USERNAME, default=current_username or ""): str,
			vol.Required(CONF_PASSWORD): str,
		})
		
		return self.async_show_form(
			step_id="reauth_confirm",
			data_schema=schema,
			errors=errors,
			description_placeholders={"username": current_username or ""},
		)
		
	async def _test_credentials(self, username: str, password: str) -> None:
		"""Test if the credentials are valid."""
		session = async_get_clientsession(self.hass)
		# Lazy import to avoid heavy imports at module load time
		from .infomentor.client import InfoMentorClient
		async with InfoMentorClient(session) as client:
			await client.login(username, password)
			
		_LOGGER.info("Successfully validated InfoMentor credentials")


class InfoMentorOptionsFlow(config_entries.OptionsFlow):
	"""Handle InfoMentor options."""

	async def async_step_init(
		self, user_input: Optional[Dict[str, Any]] = None
	) -> FlowResult:
		"""Manage notification settings."""
		current_notify = self.config_entry.options.get(CONF_NOTIFY_SERVICES, "")

		if user_input is not None:
			return self.async_create_entry(title="", data=user_input)

		schema = vol.Schema({
			vol.Optional(CONF_NOTIFY_SERVICES, default=current_notify): str,
		})

		return self.async_show_form(
			step_id="init",
			data_schema=schema,
		)
