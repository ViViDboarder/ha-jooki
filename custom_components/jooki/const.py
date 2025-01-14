"""Constants for the Jooki integration."""

DOMAIN = "jooki"
CONF_BRIDGE_PREFIX: str = "mqtt_bridge_prefix"

# Topics for interaction
PING_TOPIC = "/j/debug/input/ping"
PONG_TOPIC = "/j/debug/output/pong"
STATE_TOPIC = "/j/web/output/state"
GET_STATE_TOPIC = "/j/web/input/GET_STATE"
PLAY_TOPIC = "/j/web/input/DO_PLAY"
PAUSE_TOPIC = "/j/web/input/DO_PAUSE"
SEEK_TOPIC = "/j/web/input/SEEK"
PREV_TOPIC = "/j/web/input/DO_PREV"
NEXT_TOPIC = "/j/web/input/DO_NEXT"
VOL_TOPIC = "/j/web/input/SET_VOL"
OFF_TOPIC = "/j/web/input/SHUTDOWN"
PLAYLIST_PLAY_TOPIC = "/j/web/input/PLAYLIST_PLAY"
TOY_SAFE_TOPIC = "/j/web/input/SET_TOY_SAFE"
