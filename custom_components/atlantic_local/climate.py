"""Climate entity for Atlantic local."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtlanticLocalConfigEntry
from .api import AtlanticLocalError
from .const import (
    BOOST_DURATIONS,
    BOOST_TYPE_MAP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    TEMPERATURE_STEP,
)
from .coordinator import AtlanticLocalCoordinator
from .entity import AtlanticLocalEntity

PARALLEL_UPDATES = 1

POWER_ON = "on"
POWER_OFF = "off"
PRESET_NONE = "none"
PRESET_BOOST = "boost"
BOOST_PRESET_PREFIX = "boost_"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtlanticLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    async_add_entities([AtlanticLocalClimate(entry.runtime_data.coordinator)])


class AtlanticLocalClimate(AtlanticLocalEntity, ClimateEntity):
    """The heater, driven through its local data model."""

    _attr_name = None
    _attr_translation_key = "heater"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TEMPERATURE_STEP

    def __init__(self, coordinator: AtlanticLocalCoordinator) -> None:
        """Initialise the climate entity from the mapped ids."""
        super().__init__(coordinator, "climate")
        features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_modes = [HVACMode.HEAT]
        if coordinator.power_map is not None:
            self._attr_hvac_modes.append(HVACMode.OFF)
            features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        preset_map = coordinator.preset_map
        self._boost_presets = (
            preset_map is not None
            and PRESET_BOOST in preset_map.values
            and coordinator.data.boost_duration is not None
        )
        if self._boost_presets:
            self._attr_preset_modes = [PRESET_NONE] + [
                f"{BOOST_PRESET_PREFIX}{minutes}" for minutes in BOOST_DURATIONS
            ]
            features |= ClimateEntityFeature.PRESET_MODE
        elif preset_map is not None:
            self._attr_preset_modes = list(preset_map.values)
            features |= ClimateEntityFeature.PRESET_MODE
        if coordinator.data.boost_type is not None:
            self._attr_fan_modes = list(BOOST_TYPE_MAP.values)
            features |= ClimateEntityFeature.FAN_MODE
        self._attr_supported_features = features

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

    @property
    def hvac_mode(self) -> HVACMode:
        """Return off only when the power id says so."""
        if self.coordinator.data.power == POWER_OFF:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return whether the heater is drawing power right now."""
        data = self.coordinator.data
        if data.power == POWER_OFF:
            return HVACAction.OFF
        if data.heating_demand is None:
            return None
        return HVACAction.HEATING if data.heating_demand > 0 else HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return the active preset; a running boost is named by its duration."""
        data = self.coordinator.data
        if not self._boost_presets or data.preset != PRESET_BOOST:
            return data.preset
        preset = f"{BOOST_PRESET_PREFIX}{data.boost_duration}"
        return preset if preset in self.preset_modes else None

    @property
    def fan_mode(self) -> str | None:
        """Return the boost type: towel rail alone or with the fan."""
        return self.coordinator.data.boost_type

    async def _async_guarded(self, coro) -> None:
        try:
            await coro
        except AtlanticLocalError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write a new setpoint."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._async_guarded(
            self.coordinator.async_set_target_temperature(float(temperature))
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Switch the heater on or off."""
        power_map = self.coordinator.power_map
        if power_map is None:
            if hvac_mode == HVACMode.HEAT:
                return
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="mode_unsupported"
            )
        name = POWER_OFF if hvac_mode == HVACMode.OFF else POWER_ON
        await self._async_guarded(
            self.coordinator.async_set_mode(power_map, "power", name)
        )

    async def async_turn_on(self) -> None:
        """Switch the heater on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Switch the heater off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Write the boost type; the heater applies it to a running boost too."""
        if fan_mode not in BOOST_TYPE_MAP.values:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="mode_unsupported"
            )
        await self._async_guarded(
            self.coordinator.async_set_mode(BOOST_TYPE_MAP, "boost_type", fan_mode)
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Select a preset."""
        if self._boost_presets and preset_mode in self.preset_modes:
            if preset_mode == PRESET_NONE:
                await self._async_guarded(
                    self.coordinator.async_set_mode(
                        self.coordinator.preset_map, "preset", PRESET_NONE
                    )
                )
                return
            minutes = int(preset_mode.removeprefix(BOOST_PRESET_PREFIX))
            await self._async_guarded(self.coordinator.async_start_boost(minutes))
            return
        preset_map = self.coordinator.preset_map
        if preset_map is None or preset_mode not in preset_map.values:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="mode_unsupported"
            )
        await self._async_guarded(
            self.coordinator.async_set_mode(preset_map, "preset", preset_mode)
        )
