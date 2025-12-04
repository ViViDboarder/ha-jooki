"""Config flow for the Jooki integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast, override

import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTErrorCode
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, MQTT_PORT, PING_TOPIC, PONG_TOPIC

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
    }
)


async def async_validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> bool:
    """Return True if the device replies to a ping within 5s, otherwise False."""
    host: str = cast(str, user_input[CONF_IP_ADDRESS])

    loop = asyncio.get_running_loop()

    # Future that will be set by the callback
    reply_future: asyncio.Future[bool] = loop.create_future()

    # ----  Callback definitions ------------------------------------------------
    def on_connect(
        _client: mqtt.Client, _userdata: Any, flags: dict[str, Any], rc: MQTTErrorCode
    ) -> None:
        if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
            _LOGGER.warning(
                "MQTT connect failed (rc=%s) when validating %s", rc, host
            )
            if not reply_future.done():
                reply_future.set_result(False)

            return

        # We are connected; publish ping and subscribe for pong
        _ = _client.subscribe(PONG_TOPIC)
        _ = _client.publish(PING_TOPIC)

    def on_message(_client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage):
        """Look for a pong response."""
        if msg.topic == PONG_TOPIC and msg.payload.decode() == "HI":
            if not reply_future.done():
                reply_future.set_result(True)
            # We can disconnect early; the main coroutine will cancel anyway
            _ = _client.disconnect()

    # Random client id keeps it unique – no conflict with the device's broker.
    client = mqtt.Client(
        client_id=f"ha_jooki_validator_{host}{asyncio.get_running_loop().time()}",
        clean_session=True,
    )

    client.on_connect = on_connect
    client.on_message = on_message

    # Wrap the blocking connect in the executor
    _ = await hass.async_add_executor_job(client.connect, host, MQTT_PORT)

    # Start the network loop in a separate thread
    # The loop is run until the future is resolved or timeout.
    # Using `client.loop_start()` keeps it non‑blocking.
    _ = client.loop_start()

    try:
        _ = await asyncio.wait_for(reply_future, timeout=5.0)
        return reply_future.result()
    except asyncio.TimeoutError:
        _LOGGER.warning("Ping‑pong timeout when validating %s", host)
        return False
    finally:
        _ = client.loop_stop()
        _ = client.disconnect()

    # Return info that you want to store in the config entry.
    # return {"title": "My Jooki"}


class JookieConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jooki."""

    VERSION: int = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                success: bool = await async_validate_input(self.hass, user_input)
                if not success:
                    errors["base"] = "cannot_connect"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="My Jooki", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
