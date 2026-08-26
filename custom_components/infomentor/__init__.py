"""The InfoMentor integration."""

import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .coordinator import InfoMentorDataUpdateCoordinator
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type InfoMentorConfigEntry = ConfigEntry[InfoMentorDataUpdateCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
	"""Set up integration-wide service actions."""
	await async_register_services(hass)
	return True


async def async_setup_entry(hass: HomeAssistant, entry: InfoMentorConfigEntry) -> bool:
	"""Set up InfoMentor from a config entry."""
	_LOGGER.debug("Setting up InfoMentor integration")
	
	coordinator = InfoMentorDataUpdateCoordinator(
		hass,
		entry.data[CONF_USERNAME],
		entry.data[CONF_PASSWORD],
		entry.entry_id,
	)
	
	try:
		# Add timeout protection for the first refresh
		await asyncio.wait_for(
			coordinator.async_config_entry_first_refresh(),
			timeout=120  # 2 minutes timeout
		)
	except asyncio.TimeoutError:
		await coordinator.async_shutdown()
		_LOGGER.error("InfoMentor setup timed out after 2 minutes")
		raise ConfigEntryNotReady("Setup timeout") from None
	except ConfigEntryAuthFailed:
		await coordinator.async_shutdown()
		raise
	except asyncio.CancelledError:
		await coordinator.async_shutdown()
		raise
	except Exception as err:
		await coordinator.async_shutdown()
		_LOGGER.error("Failed to authenticate with InfoMentor: %s", err)
		raise ConfigEntryNotReady from err
	
	entry.runtime_data = coordinator
	
	# Set up platforms with timeout protection
	try:
		await asyncio.wait_for(
			hass.config_entries.async_forward_entry_setups(entry, PLATFORMS),
			timeout=60  # 1 minute for platform setup
		)
	except asyncio.TimeoutError:
		await coordinator.async_shutdown()
		_LOGGER.error("Platform setup timed out after 1 minute")
		raise ConfigEntryNotReady("Platform setup timeout") from None
	except asyncio.CancelledError:
		await coordinator.async_shutdown()
		raise
	except Exception:
		await coordinator.async_shutdown()
		raise
	
	# Register device for the InfoMentor account
	device_registry = dr.async_get(hass)
	device_registry.async_get_or_create(
		config_entry_id=entry.entry_id,
		identifiers={(DOMAIN, entry.data[CONF_USERNAME])},
		manufacturer="InfoMentor",
		name=f"InfoMentor Account ({entry.data[CONF_USERNAME]})",
		model="Hub",
	)
	
	return True


async def async_unload_entry(hass: HomeAssistant, entry: InfoMentorConfigEntry) -> bool:
	"""Unload a config entry."""
	_LOGGER.debug("Unloading InfoMentor integration")
	
	# Unload platforms
	unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
	
	if unload_ok:
		await entry.runtime_data.async_shutdown()
	
	return unload_ok
