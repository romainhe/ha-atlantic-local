"""Data update coordinator for Atlantic local."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AtlanticLocalApi, AtlanticLocalError, DeviceIdentity, Value
from .const import (
    BOOST_TYPE_MAP,
    DOMAIN,
    ID_BOOST,
    ID_BOOST_DURATION,
    ID_BOOST_END,
    ID_ENERGY,
    ID_HEATING_DEMAND,
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


def local_epoch_to_datetime(value: Value | None) -> datetime | None:
    """Decode the module's timestamps, 0 meaning unset.

    The module stores local wall-clock time as if it were a UTC epoch, so the
    UTC fields are kept and the local time zone attached afterwards.
    """
    if not isinstance(value, int) or value <= 0:
        return None
    wall_clock = datetime.fromtimestamp(value, UTC)
    return wall_clock.replace(tzinfo=dt_util.get_default_time_zone())


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
    boost_type: str | None = None
    boost_duration: int | None = None
    boost_end: datetime | None = None
    energy: int | None = None
    heating_demand: int | None = None

    @classmethod
    def from_values(
        cls,
        values: dict[int, Value],
        preset_map: ModeMap | None = None,
        power_map: ModeMap | None = None,
    ) -> AtlanticState:
        """Build a state from raw data-model values."""
        rssi = values.get(ID_WIFI_RSSI)
        duration = values.get(ID_BOOST_DURATION)
        energy = values.get(ID_ENERGY)
        demand = values.get(ID_HEATING_DEMAND)
        return cls(
            target_temperature=centi_to_celsius(values.get(ID_TARGET_TEMPERATURE)),
            room_temperature=centi_to_celsius(values.get(ID_ROOM_TEMPERATURE)),
            internal_temperature=centi_to_celsius(values.get(ID_INTERNAL_TEMPERATURE)),
            min_temperature=centi_to_celsius(values.get(ID_MIN_SETPOINT)),
            max_temperature=centi_to_celsius(values.get(ID_MAX_SETPOINT)),
            wifi_rssi=rssi if isinstance(rssi, int) else None,
            preset=_lookup(preset_map, values),
            power=_lookup(power_map, values),
            boost_type=_lookup(BOOST_TYPE_MAP, values),
            boost_duration=duration if isinstance(duration, int) else None,
            boost_end=local_epoch_to_datetime(values.get(ID_BOOST_END)),
            energy=energy if isinstance(energy, int) else None,
            heating_demand=demand if isinstance(demand, int) else None,
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

    async def _async_written(self, **changes: Any) -> None:
        """Show an accepted write at once, then re-read in the background.

        The refresh is debounced: without the immediate update a second
        command sent within the cooldown would leave the old state displayed.
        """
        self.async_set_updated_data(replace(self.data, **changes))
        await self.async_request_refresh()

    async def async_set_target_temperature(self, temperature: float) -> None:
        """Write a new setpoint."""
        await self.api.async_write(ID_TARGET_TEMPERATURE, round(temperature * 100))
        await self._async_written(target_temperature=temperature)

    async def async_set_mode(self, mode_map: ModeMap, field: str, name: str) -> None:
        """Write one named value of a mode map into the given state field."""
        await self.api.async_write(
            mode_map.data_id, mode_map.values[name], key=mode_map.key
        )
        await self._async_written(**{field: name})

    async def async_start_boost(self, minutes: int) -> None:
        """Start a boost of the given length, restarting a running one.

        The heater reads the duration only when a boost starts, so a running
        boost is stopped and started again to apply a new length.
        """
        await self.api.async_write(ID_BOOST_DURATION, minutes, key="VIU")
        if self.data.preset == "boost":
            await self.api.async_write(ID_BOOST, 0, key="VIU")
        await self.api.async_write(ID_BOOST, 1, key="VIU")
        await self._async_written(boost_duration=minutes, preset="boost")

    async def async_set_boost_duration(self, minutes: int) -> None:
        """Write the boost duration, used by the next boost start."""
        await self.api.async_write(ID_BOOST_DURATION, minutes, key="VIU")
        await self._async_written(boost_duration=minutes)
