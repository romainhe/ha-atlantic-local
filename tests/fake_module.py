"""An in-memory stand-in for the module's /passthrough/cmd endpoint."""

from __future__ import annotations

import json
from typing import Any

import aiohttp

DEFAULT_VALUES: dict[int, tuple[str, Any]] = {
    1: ("VS", "100000000001"),
    50: ("VS", "TRI TD1W"),
    51: ("VS", "DORIS 2000W BLC"),
    503: ("VS", "v1.5.2"),
    822: ("VIS", -46),
    4015: ("VIU", 4),
    4019: ("VS", "Salle de bain"),
    4041: ("VIU", 496273),
    4044: ("VIU", 0),
    4045: ("VIU", 1),
    4046: ("VIU", 30),
    4048: ("VIU", 0),
    4103: ("VIS", 2219),
    4104: ("VIS", 1980),
    4110: ("VIS", 700),
    4111: ("VIS", 2800),
    4118: ("VIS", 2000),
    8503: ("VIU", 20),
}


class _Response:
    def __init__(self, text: str) -> None:
        self._text = text

    def raise_for_status(self) -> None:
        return None

    async def text(self) -> str:
        return self._text


class FakeModule:
    """Answer read and write commands like the real module does."""

    def __init__(self, values: dict[int, tuple[str, Any]] | None = None) -> None:
        self.values = dict(DEFAULT_VALUES if values is None else values)
        self.requests: list[dict[str, Any]] = []
        self.fail = False

    async def post(self, url: str, data: str) -> _Response:
        if self.fail:
            raise aiohttp.ClientError("unreachable")
        command = json.loads(data)[0]
        self.requests.append(command)
        data_id = command["ID"]
        reply: dict[str, Any] = {"SN": command["SN"], "ID": data_id}
        if command["CMD"] == 1:
            reply["CMD"] = 2
            if data_id in self.values:
                key, value = self.values[data_id]
                reply |= {key: value, "STATUS": 2}
            else:
                reply |= {"STATUS": 10, "ERROR": 6}
        else:
            reply["CMD"] = 4
            key = self.values.get(data_id, ("VIS", None))[0]
            if key in command:
                self.values[data_id] = (key, command[key])
                reply |= {key: command[key], "STATUS": 2}
            else:
                reply |= {"STATUS": 10, "ERROR": 4}
        envelope = {
            "message": "Post Action Received",
            "payload": json.dumps([reply]),
            "success": True,
        }
        return _Response(json.dumps(envelope))
