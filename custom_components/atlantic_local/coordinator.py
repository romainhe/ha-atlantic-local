"""Data update coordinator for Atlantic local."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AtlanticLocalApi, AtlanticLocalError, DeviceIdentity, Value
from .const import (
    DOMAIN,
    ID_INTERNAL_TEMPERATURE,
    ID_MAX_SETPOINT,
    ID_MIN_SETPOINT,
    ID_ROOM_TEMPERATURE,
    ID_TARGET_TEMPERATURE,
    ID_WIFI_RSSI,
    POLLED_IDS,
)

_LOGGER = logging.getLogger(__name__)


def centi_to_celsius(value: Value | None) -> float | None:
    """Convert a hundredths-of-degree reading to °C."""
    if not isinstance(value, int):
        return None
    return round(value / 100, 2)


@dataclass(frozen=True)
class AtlanticState:
    """One poll of the values exposed by the module."""

    target_temperature: float | None
    room_temperature: float | None
    internal_temperature: float | None
    min_temperature: float | None
    max_temperature: float | None
    wifi_rssi: int | None

    @classmethod
    def from_values(cls, values: dict[int, Value]) -> AtlanticState:
        """Build a state from raw data-model values."""
        rssi = values.get(ID_WIFI_RSSI)
        return cls(
            target_temperature=centi_to_celsius(values.get(ID_TARGET_TEMPERATURE)),
            room_temperature=centi_to_celsius(values.get(ID_ROOM_TEMPERATURE)),
            internal_temperature=centi_to_celsius(values.get(ID_INTERNAL_TEMPERATURE)),
            min_temperature=centi_to_celsius(values.get(ID_MIN_SETPOINT)),
            max_temperature=centi_to_celsius(values.get(ID_MAX_SETPOINT)),
            wifi_rssi=rssi if isinstance(rssi, int) else None,
        )


class AtlanticLocalCoordinator(DataUpdateCoordinator[AtlanticState]):
    """Poll the module over the local network."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: AtlanticLocalApi,
        identity: DeviceIdentity,
        scan_interval: timedelta,
    ) -> None:
        """Initialise the coordinator."""
        self.api = api
        self.identity = identity
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
            config_entry=entry,
        )

    async def _async_update_data(self) -> AtlanticState:
        """Read every polled id."""
        try:
            values = await self.api.async_read_many(POLLED_IDS)
        except AtlanticLocalError as err:
            raise UpdateFailed(str(err)) from err
        return AtlanticState.from_values(values)

    async def async_set_target_temperature(self, temperature: float) -> None:
        """Write a new setpoint and refresh."""
        await self.api.async_write(ID_TARGET_TEMPERATURE, round(temperature * 100))
        await self.async_request_refresh()
