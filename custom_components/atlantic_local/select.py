"""Select entities for Atlantic local."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtlanticLocalConfigEntry
from .api import AtlanticLocalError
from .const import BOOST_TYPE_MAP, DOMAIN
from .coordinator import AtlanticLocalCoordinator
from .entity import AtlanticLocalEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtlanticLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the boost type select when the heater has one."""
    coordinator = entry.runtime_data.coordinator
    if coordinator.data.boost_type is not None:
        async_add_entities([AtlanticBoostTypeSelect(coordinator)])


class AtlanticBoostTypeSelect(AtlanticLocalEntity, SelectEntity):
    """What a boost heats: the towel rail alone or with the fan."""

    _attr_translation_key = "boost_type"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(BOOST_TYPE_MAP.values)

    def __init__(self, coordinator: AtlanticLocalCoordinator) -> None:
        """Initialise the select."""
        super().__init__(coordinator, "boost_type")

    @property
    def current_option(self) -> str | None:
        """Return the configured boost type."""
        return self.coordinator.data.boost_type

    async def async_select_option(self, option: str) -> None:
        """Write the boost type; the heater applies it to a running boost too."""
        try:
            await self.coordinator.async_set_mode(BOOST_TYPE_MAP, "boost_type", option)
        except AtlanticLocalError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
