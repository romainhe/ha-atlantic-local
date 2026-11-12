"""Sensors for Atlantic local."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtlanticLocalConfigEntry
from .coordinator import AtlanticLocalCoordinator, AtlanticState
from .entity import AtlanticLocalEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AtlanticSensorDescription(SensorEntityDescription):
    """Describe one sensor read from the coordinator state."""

    value_fn: Callable[[AtlanticState], float | int | None]


SENSORS: tuple[AtlanticSensorDescription, ...] = (
    AtlanticSensorDescription(
        key="room_temperature",
        translation_key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda state: state.room_temperature,
    ),
    AtlanticSensorDescription(
        key="internal_temperature",
        translation_key="internal_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.internal_temperature,
    ),
    AtlanticSensorDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda state: state.wifi_rssi,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtlanticLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        AtlanticLocalSensor(coordinator, description) for description in SENSORS
    )


class AtlanticLocalSensor(AtlanticLocalEntity, SensorEntity):
    """A value read from the module."""

    entity_description: AtlanticSensorDescription

    def __init__(
        self,
        coordinator: AtlanticLocalCoordinator,
        description: AtlanticSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)
