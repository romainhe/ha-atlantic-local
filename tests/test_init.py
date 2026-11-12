"""Tests for setup, entities and the config flow."""

from unittest.mock import patch

import pytest
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.atlantic_local.const import DOMAIN
from tests.fake_module import FakeModule

CLIMATE = "climate.salle_de_bain"


@pytest.fixture
def module():
    fake = FakeModule()
    with (
        patch(
            "custom_components.atlantic_local.async_get_clientsession",
            return_value=fake,
        ),
        patch(
            "custom_components.atlantic_local.config_flow.async_get_clientsession",
            return_value=fake,
        ),
    ):
        yield fake


async def _setup(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="100000000001",
        data={CONF_HOST: "192.0.2.1"},
        title="Salle de bain",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_user_flow_creates_entry(hass, module):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: " 192.0.2.1 "}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Salle de bain"
    assert result["data"] == {CONF_HOST: "192.0.2.1"}
    assert result["result"].unique_id == "100000000001"


async def test_user_flow_cannot_connect(hass, module):
    module.fail = True
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.1"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_updates_host_of_known_device(hass, module):
    entry = await _setup(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.9"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "192.0.2.9"


async def test_setup_exposes_climate_and_sensors(hass, module):
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    state = hass.states.get(CLIMATE)
    assert state.state == "heat"
    assert state.attributes[ATTR_TEMPERATURE] == 20.0
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 19.8
    assert state.attributes[ATTR_MIN_TEMP] == 7.0
    assert state.attributes[ATTR_MAX_TEMP] == 28.0

    assert hass.states.get("sensor.salle_de_bain_room_temperature").state == "19.8"
    assert hass.states.get("sensor.salle_de_bain_internal_temperature").state == "22.19"


async def test_setup_retries_when_module_unreachable(hass, module):
    module.fail = True
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_set_temperature_writes_hundredths(hass, module):
    await _setup(hass)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: CLIMATE, ATTR_TEMPERATURE: 19.5},
        blocking=True,
    )
    assert {"CMD": 3, "SN": 13, "ID": 4118, "VIS": 1950} in module.requests
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).attributes[ATTR_TEMPERATURE] == 19.5


async def test_set_temperature_rejected_raises(hass, module):
    await _setup(hass)
    module.values[4118] = ("VIU", 2000)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: CLIMATE, ATTR_TEMPERATURE: 19.5},
            blocking=True,
        )
