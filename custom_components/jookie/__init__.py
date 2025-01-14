"""The Jookie integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_BRIDGE_PREFIX, DOMAIN
from .coordinator import JookieCoordinator

_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SWITCH]

type JookieConfigEntry = ConfigEntry[JookieCoordinator]


# TODO Update entry annotation
async def async_setup_entry(hass: HomeAssistant, entry: JookieConfigEntry) -> bool:
    """Set up Jookie from a config entry."""

    bridge_prefix = entry.data[CONF_BRIDGE_PREFIX]
    coordinator = JookieCoordinator(hass, bridge_prefix)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await coordinator.async_start()

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: JookieConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)

    if coordinator is None:
        await coordinator.async_stop()

    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
