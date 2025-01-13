from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
import logging
import asyncio
import json

_LOGGER = logging.getLogger(__name__)

# Topics for interaction
PING_TOPIC = "j/debug/input/ping"
PONG_TOPIC = "j/debug/output/pong"
STATE_TOPIC = "j/web/output/state"
GET_STATE_TOPIC = "j/web/input/GET_STATE"

PING_INTERVAL = 30  # Seconds

def parse_state(payload):
    """Parse the state payload and return a structured dictionary."""
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        _LOGGER.error("Failed to parse JSON payload: %s", e)
        return {}

class JookieCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, bridge_prefix: str):
        """Initialize the Jookie coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Jookie Media Player Coordinator",
        )
        self._hass = hass
        self._mqtt = hass.components.mqtt
        self._ping_task = None
        self._missed_pongs = 0
        self._device_available = True
        self.state = {}
        self._bridge_prefix = bridge_prefix.rstrip("/")

    @property
    def available(self):
        """Return if the device is considered available."""
        return self._device_available

    async def async_publish(self, topic_suffix: str, payload: dict|str|None = None):
        """Publish a message to the MQTT broker with the bridge prefix."""
        full_topic = f"{self._bridge_prefix}/{topic_suffix}"
        try:
            if payload is None:
                payload = "{}"
            elif isinstance(payload, dict):
                payload = json.dumps(payload)
            await self._mqtt.async_publish(full_topic, payload)
        except Exception as e:
            _LOGGER.error("Error publishing to topic %s: %s", full_topic, e)

    async def _mqtt_message_received(self, msg):
        """Handle incoming MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            if topic.endswith(PONG_TOPIC):
                _LOGGER.debug("Received PONG from device.")
                self._missed_pongs = 0
                self._device_available = True
                return

            if topic.endswith(STATE_TOPIC):
                _LOGGER.debug("Received state update from device: %s", payload)
                self.state.update(parse_state(payload))
                await self.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Error processing MQTT message: %s", e)

    def get_state(self, path: str, default: Any|None=None) -> Any:
        """Gets state value from nested dictionaries using dot notation."""
        keys = path.split(".")
        value = self.state
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


    async def _send_ping(self):
        """Send a ping message to check device availability."""
        await self.async_publish(PING_TOPIC, "")

    async def _start_ping_loop(self):
        """Start a periodic ping loop."""
        while True:
            try:
                await self._send_ping()

                self._missed_pongs += 1

                if self._missed_pongs > 2:
                    _LOGGER.warning("Device is unavailable after missing multiple pongs.")
                    self._device_available = False

                await asyncio.sleep(PING_INTERVAL)

                # If no state update, request state explicitly
                if not self.state:
                    _LOGGER.warning("No state updates received; requesting state.")
                    await self.async_publish(GET_STATE_TOPIC, "{}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Error in ping loop: %s", e)

    async def async_start(self):
        """Start the coordinator."""
        _LOGGER.info("Starting Jookie Coordinator.")
        await self._mqtt.async_subscribe(f"{self._bridge_prefix}/{PONG_TOPIC}", self._mqtt_message_received)
        await self._mqtt.async_subscribe(f"{self._bridge_prefix}/{STATE_TOPIC}", self._mqtt_message_received)

        # Start the ping loop
        self._ping_task = self._hass.loop.create_task(self._start_ping_loop())

    async def async_stop(self):
        """Stop the coordinator."""
        _LOGGER.info("Stopping Jookie Coordinator.")
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None
        await self._mqtt.async_unsubscribe(f"{self._bridge_prefix}/{PONG_TOPIC}")
        await self._mqtt.async_unsubscribe(f"{self._bridge_prefix}/{STATE_TOPIC}")

