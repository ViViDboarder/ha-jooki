import logging

import homeassistant.util.dt as dt_util
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JookieConfigEntry
from .const import (
    DOMAIN,
    NEXT_TOPIC,
    OFF_TOPIC,
    PAUSE_TOPIC,
    PLAY_TOPIC,
    PLAYLIST_PLAY_TOPIC,
    PREV_TOPIC,
    SEEK_TOPIC,
    VOL_TOPIC,
)
from .coordinator import JookieCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            JookieMediaPlayer(
                "Jookie Media Player",
                hass.data[DOMAIN][entry.entry_id],
            ),
        ],
    )


class JookieMediaPlayer(CoordinatorEntity[JookieCoordinator], MediaPlayerEntity):
    """Representation of a Jookie media player device."""

    def __init__(self, name: str, coordinator: JookieCoordinator):
        """Initialize the media player."""
        super().__init__(coordinator)
        self._attr_should_poll = False

        self._attr_name = name
        self._attr_available = False
        self._attr_media_content_type = MediaType.PLAYLIST
        self._attr_device_class = MediaPlayerDeviceClass.SPEAKER
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.SEEK
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )

        # self._attr_unique_id = __
        # self._attr_device_info = DeviceInfo()
        _LOGGER.debug("Initialized Media Player: %s", self._attr_name)

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Updating data from coordinator: %s", self._attr_name)
        self._attr_available = self.coordinator.available
        _LOGGER.debug("Available %s: %s", self._attr_name, self._attr_available)

        playback_state = self.coordinator.get_state(
            "audio.playback.state", "idle"
        ).upper()
        _LOGGER.debug(
            "Playback state value for %s: %s", self._attr_name, playback_state
        )
        self._attr_state = {
            "STARTING": MediaPlayerState.BUFFERING,
            "PLAYING": MediaPlayerState.PLAYING,
            "PAUSED": MediaPlayerState.PAUSED,
            "ENDED": MediaPlayerState.IDLE,
            # Unknown
            "idle": MediaPlayerState.IDLE,
        }.get(playback_state, MediaPlayerState.IDLE)

        _LOGGER.debug(
            "Playback state attr for %s: %s", self._attr_name, self._attr_state
        )

        if self._attr_state in {
            MediaPlayerState.BUFFERING,
            MediaPlayerState.PLAYING,
            MediaPlayerState.PAUSED,
        }:
            self._attr_media_title = self.coordinator.get_state(
                "audio.nowPlaying.track"
            )
            self._attr_media_artist = self.coordinator.get_state(
                "audio.nowPlaying.artist"
            )
            self._attr_media_album_name = self.coordinator.get_state(
                "audio.nowPlaying.album"
            )
            self._attr_media_track = self.coordinator.get_state(
                "audio.nowPlaying.queueIndex"
            )
            self._attr_media_content_id = self.coordinator.get_state(
                "audio.nowPlaying.playlistId"
            )
            # TODO: Figure out what this looks like if it's not an on device playlist
            self._attr_media_playlist = self.coordinator.get_state(
                f"db.playlists.{self._attr_media_content_id}.title"
            )

            if image := self.coordinator.get_state("audio.nowPlaying.image"):
                if image.startswith("http"):
                    self._attr_media_image_url = image
            else:
                self._attr_media_image_url = None

            # Source is a playlist, probably maybe
            self._attr_source = self.coordinator.get_state(
                f"audio.nowPlaying.source"
            )

            duration_ms = self.coordinator.get_state("audio.nowPlaying.duration_ms")
            self._attr_media_duration = (
                int(duration_ms / 1000) if duration_ms is not None else None
            )

            position_ms = self.coordinator.get_state("audio.playback.position_ms")
            media_position = (
                int(position_ms / 1000) if position_ms is not None else None
            )

            if media_position != self._attr_media_position:
                self._attr_media_position = media_position
                self._attr_media_position_updated_at = dt_util.utcnow()

            volume = self.coordinator.get_state("audio.config.volume")
            self._attr_volume_level = volume / 100 if volume is not None else None

            # TODO: Set sources by iterating over the playlists at self.coordinator.get_state("db.playlists")
            # where key is ID and resulting dict contains a "title" key.
            playlists = self.coordinator.get_state("db.playlists")
            if playlists:
                self._attr_source_list = [
                    playlist["title"]
                    for playlist_id, playlist in playlists.items()
                    if playlist_id != "TRASH"
                ] + ["SPOTIFY"]
        else:
            # Not playing, so empty these out
            self._attr_media_title = None
            self._attr_media_artist = None
            self._attr_media_album_name = None
            self._attr_media_track = None
            self._attr_media_content_id = None
            self._attr_media_playlist = None
            self._attr_media_duration = None
            self._attr_media_position = None
            self._attr_media_position_updated_at = None
            self._attr_volume_level = None
            self._attr_source = None
            self._attr_media_image_url = None

        self.async_write_ha_state()

    async def async_media_play(self):
        """Send play command to the device."""
        await self.coordinator.async_publish(PLAY_TOPIC)

    async def async_media_pause(self):
        """Send pause command to the device."""
        await self.coordinator.async_publish(PAUSE_TOPIC)

    async def async_media_seek(self, position: float):
        """Send seek command to the device."""
        position_ms = int(position * 1000)
        await self.coordinator.async_publish(SEEK_TOPIC, {"position_ms": position_ms})

    async def async_media_next_track(self):
        """Send next track command to the device."""
        await self.coordinator.async_publish(NEXT_TOPIC)

    async def async_media_previous_track(self):
        """Send previous track command to the device."""
        await self.coordinator.async_publish(PREV_TOPIC)

    async def async_set_volume_level(self, volume):
        """Set volume level (0.0 to 1.0)."""
        volume_percent = int(volume * 100)
        await self.coordinator.async_publish(VOL_TOPIC, {"vol": volume_percent})

    async def async_turn_off(self):
        """Send shutdown command to the device."""
        await self.coordinator.async_publish(OFF_TOPIC)

    async def async_select_source(self, source: str):
        """Select input source."""
        _LOGGER.debug("Try setting source: %s", source)
        playlists = self.coordinator.get_state("db.playlists")
        if playlists:
            for playlist_id, playlist in playlists.items():
                _LOGGER.debug("comparing to %s", playlist["title"])
                if playlist["title"] == source:
                    await self.coordinator.async_publish(
                        PLAYLIST_PLAY_TOPIC,
                        {"playlistId": playlist_id, "trackIndex": 1},
                    )
                    break
