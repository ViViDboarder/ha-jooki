"""The Jooki integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_BRIDGE_PREFIX, DOMAIN
from .coordinator import JookiCoordinator

_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SWITCH]

type JookiConfigEntry = ConfigEntry[JookiCoordinator]


# TODO Update entry annotation
async def async_setup_entry(hass: HomeAssistant, entry: JookiConfigEntry) -> bool:
    """Set up Jooki from a config entry."""

    bridge_prefix = entry.data[CONF_BRIDGE_PREFIX]
    coordinator = JookiCoordinator(hass, bridge_prefix)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await coordinator.async_start()

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: JookiConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)

    if coordinator is None:
        await coordinator.async_stop()

    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
