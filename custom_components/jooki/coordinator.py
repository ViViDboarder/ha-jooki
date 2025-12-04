"""Data Update Coordinator for Jooki."""

import asyncio
import json
import logging
from typing import Any, cast

import paho.mqtt.client as mqtt

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import GET_STATE_TOPIC, MQTT_PORT, PING_TOPIC, PONG_TOPIC, STATE_TOPIC

_LOGGER = logging.getLogger(__name__)

JSON = dict[str, Any]


PING_INTERVAL = 30  # Seconds


def parse_state(payload: bytes) -> JSON:
    """Parse the state payload and return a structured dictionary."""
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        _LOGGER.error("Failed to parse JSON payload: %s", e)
        return {}


def merge_data(
    old_data: JSON, new_data: JSON, path: str = ""
) -> tuple[JSON, set[str]]:
    """Merge data dictionaries down and track changes."""
    changed: set[str] = set()

    for key, new_value in new_data.items():
        if (
            isinstance(new_value, dict)
            and key in old_data
            and isinstance(old_data[key], dict)
        ):
            new_value = cast(JSON, new_value)
            old_value = cast(JSON, old_data[key])

            old_data[key], re_changed = merge_data(old_value, new_value, path=f"{path}.{key}" if path else key)
            changed.update(re_changed)
        elif key not in old_data or old_data[key] != new_value:
            old_data[key] = new_value
            changed.add(f"{path}.{key}" if path else key)

    return old_data, changed


class JookiCoordinator(DataUpdateCoordinator):
    """Data Update Coordinator for Jooki."""

    def __init__(self, hass: HomeAssistant, ip_address: str):
        """Initialize the Jooki coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Jooki Media Player Coordinator",
        )
        self._hass: HomeAssistant = hass
        self._ip_address: str = ip_address
        self._client: mqtt.Client = mqtt.Client(client_id=f"homeassistant_jooki_{ip_address}", clean_session=True)
        self._ping_task = None
        self._missed_pongs: int = 0
        self._device_available: bool = False
        self.data: dict[str, Any] = {}

    @property
    def available(self):
        """Return if the device is considered available."""
        return self._device_available

    async def async_connect(self):
        """Connect to the MQTT broker."""
        result = await self._hass.async_add_executor_job(self._client.connect, self._ip_address, MQTT_PORT)
        if result != 0:
            _LOGGER.error("Failed to connect to Jooki MQTT broker at %s:%s", self._ip_address, MQTT_PORT)
            self._device_available = False
        else:
            _LOGGER.info("Connected to Jooki MQTT broker at %s:%s", self._ip_address, MQTT_PORT)

    async def async_publish(self, topic: str, payload: JSON | str | None = "{}"):
        """Publish a message to the MQTT broker with the bridge prefix."""
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        _LOGGER.debug("Publishing payload to topic %s: %s", topic, payload)

        _ = self._client.publish(topic, payload)

    async def _mqtt_message_received(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage):
        """Handle incoming MQTT messages."""
        topic = msg.topic
        payload = msg.payload

        if topic == PONG_TOPIC:
            _LOGGER.debug("Received PONG from device.")
            self._missed_pongs = 0
            self._device_available = True
            self.async_set_updated_data(self.data)
            return

        if topic == STATE_TOPIC:
            _LOGGER.debug("Received state update from device: %s", payload)
            try:
                message_data = parse_state(payload)
                self.data, changed = merge_data(self.data, message_data)
                # Notify only if there are meaningful changes
                if changed and changed != {"audio.playback.position_ms"}:
                    self.async_set_updated_data(self.data)

            except json.JSONDecodeError as e:
                _LOGGER.error("Error decoding MQTT message: %s", e)

    def get_state(self, path: str, default: Any | None = None) -> Any | None:
        """Get the state value from nested dictionaries using dot notation."""
        keys = path.split(".")
        value: Any = self.data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                value = default
                break

        return value

    async def _send_ping(self):
        """Send a ping message to check device availability."""
        await self.async_publish(PING_TOPIC)

    async def _start_ping_loop(self):
        """Start a periodic ping loop."""
        try:
            while True:
                # TODO: When stopped, I can also stop worying about pinging or
                # delay pings and listen again on `/j/nfc/input/tag`
                await self._send_ping()

                self._missed_pongs += 1

                if self._missed_pongs > 2 and self._device_available:
                    _LOGGER.warning(
                        "Device is unavailable after missing multiple pongs."
                    )
                    self._device_available = False
                    self.async_set_updated_data(self.data)

                await asyncio.sleep(PING_INTERVAL)

                # If no state or no db present, ask for a refresh the full device state
                if (
                    self._device_available
                    and not (
                        self.data
                        and self.get_state("db")
                    )
                ):
                    _LOGGER.debug("No state updates received; requesting state.")
                    await self.async_publish(GET_STATE_TOPIC)

        except asyncio.CancelledError:
            return

    async def async_start(self):
        """Start the coordinator."""
        _LOGGER.info("Starting Jooki Coordinator.")
        await self.async_connect()

        self._client.on_message = self._mqtt_message_received
        _ = self._client.subscribe(PONG_TOPIC)
        _ = self._client.subscribe(STATE_TOPIC)

        # Start the ping loop
        self._ping_task = self._hass.loop.create_task(self._start_ping_loop())

    async def async_stop(self):
        """Stop the coordinator."""
        _LOGGER.info("Stopping Jooki Coordinator.")
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None
