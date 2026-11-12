"""Shared entity base for Atlantic local."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AtlanticLocalCoordinator


class AtlanticLocalEntity(CoordinatorEntity[AtlanticLocalCoordinator]):
    """Base entity bound to the heater device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AtlanticLocalCoordinator, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        identity = coordinator.identity
        self._attr_unique_id = f"{identity.serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identity.serial)},
            name=identity.room_name or identity.model or "Atlantic",
            manufacturer="Atlantic",
            model=identity.model,
            model_id=identity.product_code,
            serial_number=identity.serial,
            sw_version=identity.firmware,
            configuration_url=f"http://{coordinator.config_entry.data[CONF_HOST]}/",
        )
