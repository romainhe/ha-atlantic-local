"""Climate entity for Atlantic local."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtlanticLocalConfigEntry
from .api import AtlanticLocalError
from .const import DEFAULT_MAX_TEMP, DEFAULT_MIN_TEMP, DOMAIN, TEMPERATURE_STEP
from .entity import AtlanticLocalEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtlanticLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    async_add_entities([AtlanticLocalClimate(entry.runtime_data.coordinator)])


class AtlanticLocalClimate(AtlanticLocalEntity, ClimateEntity):
    """The heater, driven through its local setpoint."""

    _attr_name = None
    _attr_translation_key = "heater"
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TEMPERATURE_STEP

    def __init__(self, coordinator) -> None:
        """Initialise the climate entity."""
        super().__init__(coordinator, "climate")

    @property
    def current_temperature(self) -> float | None:
        """Return the room temperature."""
        return self.coordinator.data.room_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the setpoint."""
        return self.coordinator.data.target_temperature

    @property
    def min_temp(self) -> float:
        """Return the lowest setpoint the heater accepts."""
        return self.coordinator.data.min_temperature or DEFAULT_MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return the highest setpoint the heater accepts."""
        return self.coordinator.data.max_temperature or DEFAULT_MAX_TEMP

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write a new setpoint."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        try:
            await self.coordinator.async_set_target_temperature(float(temperature))
        except AtlanticLocalError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Only heating is exposed until the mode ids are mapped."""
        if hvac_mode != HVACMode.HEAT:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="mode_unsupported"
            )
