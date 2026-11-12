"""Tests for presets and on/off once their ids are mapped."""

from unittest.mock import patch

import pytest
from homeassistant.components.climate import (
    ATTR_HVAC_MODES,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, CONF_HOST
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.atlantic_local.const import DOMAIN, ModeMap
from tests.fake_module import FakeModule

CLIMATE = "climate.salle_de_bain"
PRESETS = ModeMap(9001, {"comfort": 1, "eco": 2, "program": 4})
POWER = ModeMap(9002, {"on": 1, "off": 0})


@pytest.fixture
def module():
    fake = FakeModule()
    fake.values[9001] = ("VIU", 4)
    fake.values[9002] = ("VIU", 1)
    with patch(
        "custom_components.atlantic_local.async_get_clientsession",
        return_value=fake,
    ):
        yield fake


async def _setup(hass, presets=PRESETS, power=POWER):
    with (
        patch("custom_components.atlantic_local.coordinator.PRESET_MAP", presets),
        patch("custom_components.atlantic_local.coordinator.POWER_MAP", power),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN, unique_id="100000000001", data={CONF_HOST: "192.0.2.1"}
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_unmapped_modes_expose_heat_only(hass, module):
    await _setup(hass, presets=None, power=None)
    state = hass.states.get(CLIMATE)
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.HEAT]
    assert ATTR_PRESET_MODES not in state.attributes
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: CLIMATE, "hvac_mode": HVACMode.OFF},
            blocking=True,
        )


async def test_mapped_modes_are_read(hass, module):
    await _setup(hass)
    state = hass.states.get(CLIMATE)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_PRESET_MODES] == ["comfort", "eco", "program"]
    assert state.attributes[ATTR_PRESET_MODE] == "program"
    assert state.attributes[ATTR_SUPPORTED_FEATURES] & ClimateEntityFeature.TURN_OFF


async def test_set_preset_writes_raw_value(hass, module):
    await _setup(hass)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: CLIMATE, ATTR_PRESET_MODE: "eco"},
        blocking=True,
    )
    assert {"CMD": 3, "SN": 13, "ID": 9001, "VIU": 2} in module.requests
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).attributes[ATTR_PRESET_MODE] == "eco"


async def test_turn_off_writes_power_id(hass, module):
    await _setup(hass)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE, "hvac_mode": HVACMode.OFF},
        blocking=True,
    )
    assert {"CMD": 3, "SN": 13, "ID": 9002, "VIU": 0} in module.requests
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).state == HVACMode.OFF
