"""Number entities for Atlantic local."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtlanticLocalConfigEntry
from .api import AtlanticLocalError
from .const import (
    BOOST_DURATION_MAX,
    BOOST_DURATION_MIN,
    BOOST_DURATION_STEP,
    DOMAIN,
)
from .coordinator import AtlanticLocalCoordinator
from .entity import AtlanticLocalEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtlanticLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the boost duration when the heater has one."""
    coordinator = entry.runtime_data.coordinator
    if coordinator.data.boost_duration is not None:
        async_add_entities([AtlanticBoostDurationNumber(coordinator)])


class AtlanticBoostDurationNumber(AtlanticLocalEntity, NumberEntity):
    """Length of the next boost.

    The heater only reads it when a boost starts: changing it during a boost
    keeps the current end time until the boost is restarted.
    """

    _attr_translation_key = "boost_duration"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = BOOST_DURATION_MIN
    _attr_native_max_value = BOOST_DURATION_MAX
    _attr_native_step = BOOST_DURATION_STEP
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AtlanticLocalCoordinator) -> None:
        """Initialise the number."""
        super().__init__(coordinator, "boost_duration")

    @property
    def native_value(self) -> int | None:
        """Return the configured boost duration."""
        return self.coordinator.data.boost_duration

    async def async_set_native_value(self, value: float) -> None:
        """Write a new boost duration."""
        try:
            await self.coordinator.async_set_boost_duration(round(value))
        except AtlanticLocalError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
