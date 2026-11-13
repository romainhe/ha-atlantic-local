"""Tests for power, boost and its settings on the mapped Doris ids."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.climate import (
    ATTR_HVAC_MODES,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    HVACMode,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, STATE_UNKNOWN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.atlantic_local.const import DOMAIN
from custom_components.atlantic_local.coordinator import local_epoch_to_datetime
from tests.fake_module import FakeModule

CLIMATE = "climate.salle_de_bain"
BOOST_TYPE = "select.salle_de_bain_boost_type"
BOOST_DURATION = "select.salle_de_bain_boost_duration"
BOOST_END = "sensor.salle_de_bain_boost_end"
# Read on the heater after a 25 min boost started at 11:45:34 Paris time.
BOOST_END_RAW = 1794571834


@pytest.fixture
def module():
    fake = FakeModule()
    with patch(
        "custom_components.atlantic_local.async_get_clientsession",
        return_value=fake,
    ):
        yield fake


async def _setup(hass) -> None:
    await hass.config.async_set_time_zone("Europe/Paris")
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="100000000001", data={CONF_HOST: "192.0.2.1"}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _call(hass, domain, service, data) -> None:
    await hass.services.async_call(domain, service, data, blocking=True)
    await hass.async_block_till_done()


async def test_climate_exposes_power_and_boost(hass, module):
    await _setup(hass)
    state = hass.states.get(CLIMATE)
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.HEAT, HVACMode.OFF]
    assert state.attributes[ATTR_PRESET_MODES] == ["none", "boost"]
    assert state.attributes[ATTR_PRESET_MODE] == "none"


async def test_power_off_and_on_write_4015(hass, module):
    await _setup(hass)
    await _call(
        hass,
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE, "hvac_mode": HVACMode.OFF},
    )
    assert {"CMD": 3, "SN": 13, "ID": 4015, "VIU": 0} in module.requests
    assert hass.states.get(CLIMATE).state == HVACMode.OFF

    await _call(
        hass,
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE, "hvac_mode": HVACMode.HEAT},
    )
    assert {"CMD": 3, "SN": 13, "ID": 4015, "VIU": 4} in module.requests
    assert hass.states.get(CLIMATE).state == HVACMode.HEAT
    assert not any(r["CMD"] == 3 and r["ID"] == 4030 for r in module.requests), (
        "4030 cancels the boost instead of switching off"
    )


async def test_boost_preset_starts_and_stops(hass, module):
    await _setup(hass)
    await _call(
        hass,
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: CLIMATE, ATTR_PRESET_MODE: "boost"},
    )
    assert {"CMD": 3, "SN": 13, "ID": 4044, "VIU": 1} in module.requests
    assert hass.states.get(CLIMATE).attributes[ATTR_PRESET_MODE] == "boost"

    await _call(
        hass,
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: CLIMATE, ATTR_PRESET_MODE: "none"},
    )
    assert {"CMD": 3, "SN": 13, "ID": 4044, "VIU": 0} in module.requests
    assert hass.states.get(CLIMATE).attributes[ATTR_PRESET_MODE] == "none"


async def test_boost_type_select(hass, module):
    await _setup(hass)
    assert hass.states.get(BOOST_TYPE).state == "towel_fan"
    await _call(
        hass,
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: BOOST_TYPE, ATTR_OPTION: "towel"},
    )
    assert {"CMD": 3, "SN": 13, "ID": 4045, "VIU": 0} in module.requests
    assert hass.states.get(BOOST_TYPE).state == "towel"


async def test_boost_duration_select(hass, module):
    await _setup(hass)
    state = hass.states.get(BOOST_DURATION)
    assert state.state == "30"
    assert state.attributes["options"] == ["5", "10", "15", "20", "25", "30"]
    await _call(
        hass,
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: BOOST_DURATION, ATTR_OPTION: "15"},
    )
    assert {"CMD": 3, "SN": 13, "ID": 4046, "VIU": 15} in module.requests
    assert hass.states.get(BOOST_DURATION).state == "15"


async def test_boost_duration_outside_steps_is_unknown(hass, module):
    module.values[4046] = ("VIU", 45)
    await _setup(hass)
    assert hass.states.get(BOOST_DURATION).state == STATE_UNKNOWN


async def test_boost_end_sensor(hass, module):
    module.values[4048] = ("VIU", BOOST_END_RAW)
    await _setup(hass)
    assert hass.states.get(BOOST_END).state == "2026-11-13T11:10:34+00:00"


async def test_boost_end_unknown_without_boost(hass, module):
    await _setup(hass)
    assert hass.states.get(BOOST_END).state == STATE_UNKNOWN


async def test_boost_settings_skipped_when_heater_lacks_them(hass, module):
    for data_id in (4045, 4046):
        del module.values[data_id]
    await _setup(hass)
    assert hass.states.get(BOOST_TYPE) is None
    assert hass.states.get(BOOST_DURATION) is None


async def test_local_epoch_is_local_wall_clock(hass):
    await hass.config.async_set_time_zone("Europe/Paris")
    paris = ZoneInfo("Europe/Paris")
    assert local_epoch_to_datetime(BOOST_END_RAW) == datetime(
        2026, 11, 13, 12, 10, 34, tzinfo=paris
    )
    assert local_epoch_to_datetime(0) is None
    assert local_epoch_to_datetime(None) is None


async def test_energy_counter_in_kwh(hass, module):
    await _setup(hass)
    state = hass.states.get("sensor.salle_de_bain_energy")
    assert float(state.state) == pytest.approx(496.273)
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["state_class"] == "total_increasing"


async def test_heating_demand_drives_hvac_action(hass, module):
    await _setup(hass)
    assert hass.states.get("sensor.salle_de_bain_heating_demand").state == "20"
    assert hass.states.get(CLIMATE).attributes["hvac_action"] == "heating"

    module.values[8503] = ("VIU", 0)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).attributes["hvac_action"] == "idle"

    await _call(
        hass,
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE, "hvac_mode": HVACMode.OFF},
    )
    assert hass.states.get(CLIMATE).attributes["hvac_action"] == "off"
