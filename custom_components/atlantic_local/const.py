"""Constants for the Atlantic local integration."""

from __future__ import annotations

from dataclasses import dataclass, field

DOMAIN = "atlantic_local"

API_TIMEOUT = 10
CMD_PATH = "/passthrough/cmd"

CMD_READ = 1
CMD_READ_REPLY = 2
CMD_WRITE = 3
CMD_WRITE_REPLY = 4
STATUS_OK = 2

# The module echoes SN back; the web UI hardcodes 13 for writes.
WRITE_SN = 13

ID_SERIAL = 1
ID_PRODUCT_CODE = 50
ID_MODEL = 51
ID_FIRMWARE = 503
ID_WIFI_RSSI = 822
ID_ROOM_NAME = 4019
# 4030 and 4083 mirror 4015 but writing them does not switch the heater off:
# writing 4030 only cancels a running boost.
ID_POWER = 4015
ID_BOOST = 4044
ID_BOOST_VENTILATION = 4045
ID_BOOST_DURATION = 4046
ID_BOOST_END = 4048
ID_INTERNAL_TEMPERATURE = 4103
ID_ROOM_TEMPERATURE = 4104
ID_MIN_SETPOINT = 4110
ID_MAX_SETPOINT = 4111
ID_TARGET_TEMPERATURE = 4118

POLLED_IDS: tuple[int, ...] = (
    ID_TARGET_TEMPERATURE,
    ID_ROOM_TEMPERATURE,
    ID_INTERNAL_TEMPERATURE,
    ID_MIN_SETPOINT,
    ID_MAX_SETPOINT,
    ID_WIFI_RSSI,
    ID_BOOST_VENTILATION,
    ID_BOOST_DURATION,
    ID_BOOST_END,
)

DEFAULT_MIN_TEMP = 7.0
DEFAULT_MAX_TEMP = 28.0
TEMPERATURE_STEP = 0.5

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 600

BOOST_DURATION_MIN = 5
BOOST_DURATION_MAX = 60
BOOST_DURATION_STEP = 5


@dataclass(frozen=True)
class ModeMap:
    """How one enumerated data-model id maps to Home Assistant states."""

    data_id: int
    values: dict[str, int] = field(default_factory=dict)
    key: str = "VIU"


# Preset names must have a translation under entity.climate.heater in
# strings.json.
PRESET_MAP: ModeMap | None = ModeMap(ID_BOOST, {"none": 0, "boost": 1})
POWER_MAP: ModeMap | None = ModeMap(ID_POWER, {"on": 4, "off": 0})
BOOST_TYPE_MAP = ModeMap(ID_BOOST_VENTILATION, {"towel": 0, "towel_fan": 1})
