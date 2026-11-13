"""Select entities for Atlantic local."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtlanticLocalConfigEntry
from .api import AtlanticLocalError
from .const import BOOST_DURATIONS, BOOST_TYPE_MAP, DOMAIN
from .coordinator import AtlanticLocalCoordinator
from .entity import AtlanticLocalEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtlanticLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the boost selects the heater supports."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = []
    if coordinator.data.boost_type is not None:
        entities.append(AtlanticBoostTypeSelect(coordinator))
    if coordinator.data.boost_duration is not None:
        entities.append(AtlanticBoostDurationSelect(coordinator))
    async_add_entities(entities)


async def _async_write(coro) -> None:
    try:
        await coro
    except AtlanticLocalError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="write_failed",
            translation_placeholders={"error": str(err)},
        ) from err


class AtlanticBoostTypeSelect(AtlanticLocalEntity, SelectEntity):
    """What a boost heats: the towel rail alone or with the fan."""

    _attr_translation_key = "boost_type"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(BOOST_TYPE_MAP.values)

    def __init__(self, coordinator: AtlanticLocalCoordinator) -> None:
        """Initialise the select."""
        super().__init__(coordinator, "boost_type")

    @property
    def current_option(self) -> str | None:
        """Return the configured boost type."""
        return self.coordinator.data.boost_type

    async def async_select_option(self, option: str) -> None:
        """Write the boost type; the heater applies it to a running boost too."""
        await _async_write(
            self.coordinator.async_set_mode(BOOST_TYPE_MAP, "boost_type", option)
        )


class AtlanticBoostDurationSelect(AtlanticLocalEntity, SelectEntity):
    """Length of the next boost, in the 5 min steps the heater offers.

    The heater only reads it when a boost starts: changing it during a boost
    keeps the current end time until the boost is restarted.
    """

    _attr_translation_key = "boost_duration"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = [str(minutes) for minutes in BOOST_DURATIONS]

    def __init__(self, coordinator: AtlanticLocalCoordinator) -> None:
        """Initialise the select."""
        super().__init__(coordinator, "boost_duration")

    @property
    def current_option(self) -> str | None:
        """Return the configured duration, if it is one of the heater's steps."""
        option = str(self.coordinator.data.boost_duration)
        return option if option in self.options else None

    async def async_select_option(self, option: str) -> None:
        """Write a new boost duration."""
        await _async_write(self.coordinator.async_set_boost_duration(int(option)))
