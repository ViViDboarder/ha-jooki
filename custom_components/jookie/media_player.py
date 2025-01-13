from homeassistant.components.media_player import MediaPlayerDeviceClass, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from datetime import datetime

from homeassistant.core import callback


class JookieMediaPlayer(MediaPlayerEntity):
    """Representation of a Jookie media player device."""

    def __init__(self, name: str, coordinator):
        """Initialize the media player."""
        self.coordinator = coordinator

        self._attr_name = name
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
        )

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._attr_available = self.coordinator.available

        playback_state = self.coordinator.get_state("audio.state", "idle")
        self._attr_state = {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "idle": MediaPlayerState.IDLE,
        }.get(playback_state, MediaPlayerState.IDLE)

        self._attr_media_title = self.coordinator.get_state("audio.nowPlaying.track")
        self._attr_media_artist = self.coordinator.get_state("audio.nowPlaying.artist")
        self._attr_media_album_name = self.coordinator.get_state("audio.nowPlaying.album")
        self._attr_media_track = self.coordinator.get_state("audio.nowPlaying.queueIndex")
        self._attr_media_content_id = self.coordinator.get_state("audio.nowPlaying.playlistId")
        if self._attr_media_content_id is not None:
            self._attr_media_playlist = self.coordinator.get_state(f"db.playlists.{self._attr_media_content_id}.title")
        else:
            self._attr_media_playlist = None

        duration_ms = self.coordinator.get_state("audio.nowPlaying.duration_ms")
        self._attr_media_duration = duration_ms / 1000 if duration_ms is not None else None

        position_ms = self.coordinator.get_state("audio.playback.position_ms")
        media_position = position_ms / 1000 if position_ms is not None else None
        self._attr_media_position = media_position

        if media_position != self._attr_media_position:
            self._attr_media_position_updated_at = datetime.now()

        volume = self.coordinator.get_state("audio.config.volume")
        self._attr_volume_level = volume / 100 if volume is not None else None

        # TODO: Set sources by iterating over the playlists at self.coordinator.get_state("db.playlists")
        # wher key is ID and resulting dict contains a "title" key.

        self.async_write_ha_state()

    async def async_media_play(self):
        """Send play command to the device."""
        await self.coordinator.async_publish("j/web/input/DO_PLAY")

    async def async_media_pause(self):
        """Send pause command to the device."""
        await self.coordinator.async_publish("j/web/input/DO_PAUSE")

    async def async_media_seek(self, position: float):
        """Send seek command to the device."""
        position_ms = int(position * 1000)
        await self.coordinator.async_publish("j/web/input/SEEK", {"position_ms": position_ms})

    async def async_media_next_track(self):
        """Send next track command to the device."""
        await self.coordinator.async_publish("j/web/input/DO_NEXT")

    async def async_media_previous_track(self):
        """Send previous track command to the device."""
        await self.coordinator.async_publish("j/web/input/DO_PREV")

    async def async_set_volume_level(self, volume):
        """Set volume level (0.0 to 1.0)."""
        volume_percent = int(volume * 100)
        await self.coordinator.async_publish("j/web/input/SET_VOL", {"vol": volume_percent})

    async def async_turn_off(self):
        """Send shutdown command to the device."""
        await self.coordinator.async_publish("j/web/input/SHUTDOWN")

