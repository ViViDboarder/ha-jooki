"""Switches for Jooki."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JookiConfigEntry
from .const import DOMAIN, TOY_SAFE_TOPIC
from .coordinator import JookiCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki switches."""
    async_add_entities(
        [
            JookiSwitch(
                "Jooki Media Player Toy Safe",
                hass.data[DOMAIN][entry.entry_id],
                state_attr="device.toy_safe",
                write_topic=TOY_SAFE_TOPIC,
                turn_on={"enable": True},
                turn_off={"enable": False},
            ),
        ],
    )


class JookiSwitch(CoordinatorEntity[JookiCoordinator], SwitchEntity):
    """Representation of a Jooki switch device."""

    def __init__(
        self,
        name: str,
        coordinator: JookiCoordinator,
        state_attr: str,
        write_topic: str,
        turn_on: dict,
        turn_off: dict,
    ):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_should_poll = False

        self._attr_name = name
        self._attr_available = False
        self._state_attr = state_attr
        self._write_topic = write_topic
        self._turn_on_data = turn_on
        self._turn_off_data = turn_off

        # self._attr_unique_id = __
        # self._attr_device_info = DeviceInfo()
        _LOGGER.debug("Initialized switch: %s", self._attr_name)

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._attr_available = self.coordinator.available

        is_on = self.coordinator.get_state(self._state_attr)
        if self._attr_is_on != is_on:
            self._attr_is_on = is_on
            self.async_write_ha_state()

    async def async_turn_on(self):
        """Turn on switch."""
        await self.coordinator.async_publish(self._write_topic, self._turn_on_data)

    async def async_turn_off(self):
        """Turn off switch."""
        await self.coordinator.async_publish(self._write_topic, self._turn_off_data)
