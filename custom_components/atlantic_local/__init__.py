"""The Atlantic local integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AtlanticLocalApi, AtlanticLocalError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import AtlanticLocalCoordinator

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SENSOR,
]


@dataclass
class AtlanticLocalRuntimeData:
    """Runtime objects attached to the config entry."""

    coordinator: AtlanticLocalCoordinator


AtlanticLocalConfigEntry = ConfigEntry[AtlanticLocalRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: AtlanticLocalConfigEntry
) -> bool:
    """Set up Atlantic local from a config entry."""
    api = AtlanticLocalApi(async_get_clientsession(hass), entry.data[CONF_HOST])
    try:
        identity = await api.async_identity()
    except AtlanticLocalError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = AtlanticLocalCoordinator(
        hass,
        entry,
        api,
        identity,
        timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = AtlanticLocalRuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: AtlanticLocalConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: AtlanticLocalConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
