# ha-jooki

Jooki Media Player custom component for Home Assistant

## Background

The Jooki media player provides a mobile app and a web UI. While the Jooki seems to be discontinued, the web interface hosted on the Jooki's local IP still works. These interfaces are powered by MQTT messages.

## Installation

Since the Jooki acts as it's own broker, to use this component you need bridge the Jooki to your Home Assistant MQTT broker. From there, the component will be able to read and publish MQTT messages to interface with the Jooki.

 1. Install the Mosquitto Broker addon
 2. Configure the `customize` section to tell it to read custom files from a folder. For example: `{active: true, folder: mosquitto}`. If you already have a folder definied,, you don't need to change it. Use that folder path below instead.
 3. Either using the Samba or SSH addons, open `/share/mosquitto` (or the folder defined above) add the following example bridge file to bridge your Jooki.
 4. Replace the IP address with the IP address of your Jooki device
 5. Restart the MQTT addon
 6. (Optional) If you have multiple Jookis, you'll need to create multiple copies with distinct connection names and distinct topic prefixes. Eg. `br-jookie1` and `jookie1/`.
 7. Install this addon. If you have `unhacs`, use the following over SSH from your HA config directory: `unhacs add https://github.com/ViViDboarder/ha-jookie`
 8. Restart Home Assistant `ha core restart`
 9. Turn on your Jooki
10. Add integration from Devices screen and add bride prefix from your config file. Eg. `jookie/`

### Example bridge config

    # Bridge to jooki
    connection br-jooki
    #          ^ This bridge name must be unique per device
    address 192.168.3.101:1883
    #       ^ Use your actual device IP
    topic # out 0 jooki/ ""
    #             ^ This prefix must be unique per device
    topic # in 0 jooki/ ""
    #            ^ This prefix must be unique per device
