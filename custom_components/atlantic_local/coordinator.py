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
    POWER_MAP,
    PRESET_MAP,
    ModeMap,
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
    preset: str | None = None
    power: str | None = None

    @classmethod
    def from_values(
        cls,
        values: dict[int, Value],
        preset_map: ModeMap | None = None,
        power_map: ModeMap | None = None,
    ) -> AtlanticState:
        """Build a state from raw data-model values."""
        rssi = values.get(ID_WIFI_RSSI)
        return cls(
            target_temperature=centi_to_celsius(values.get(ID_TARGET_TEMPERATURE)),
            room_temperature=centi_to_celsius(values.get(ID_ROOM_TEMPERATURE)),
            internal_temperature=centi_to_celsius(values.get(ID_INTERNAL_TEMPERATURE)),
            min_temperature=centi_to_celsius(values.get(ID_MIN_SETPOINT)),
            max_temperature=centi_to_celsius(values.get(ID_MAX_SETPOINT)),
            wifi_rssi=rssi if isinstance(rssi, int) else None,
            preset=_lookup(preset_map, values),
            power=_lookup(power_map, values),
        )


def _lookup(mode_map: ModeMap | None, values: dict[int, Value]) -> str | None:
    """Return the name a mode map gives to the value read for its id."""
    if mode_map is None:
        return None
    raw = values.get(mode_map.data_id)
    return next((name for name, v in mode_map.values.items() if v == raw), None)


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
        self.preset_map = PRESET_MAP
        self.power_map = POWER_MAP
        self._polled_ids = POLLED_IDS + tuple(
            m.data_id for m in (PRESET_MAP, POWER_MAP) if m is not None
        )
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
            values = await self.api.async_read_many(self._polled_ids)
        except AtlanticLocalError as err:
            raise UpdateFailed(str(err)) from err
        return AtlanticState.from_values(values, self.preset_map, self.power_map)

    async def async_set_target_temperature(self, temperature: float) -> None:
        """Write a new setpoint and refresh."""
        await self.api.async_write(ID_TARGET_TEMPERATURE, round(temperature * 100))
        await self.async_request_refresh()

    async def async_set_mode(self, mode_map: ModeMap, name: str) -> None:
        """Write one named value of a mode map and refresh."""
        await self.api.async_write(
            mode_map.data_id, mode_map.values[name], key=mode_map.key
        )
        await self.async_request_refresh()
