"""Async client for the local web server of Atlantic Wi-Fi modules."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import (
    API_TIMEOUT,
    CMD_PATH,
    CMD_READ,
    CMD_WRITE,
    CMD_WRITE_REPLY,
    ID_FIRMWARE,
    ID_MODEL,
    ID_PRODUCT_CODE,
    ID_ROOM_NAME,
    ID_SERIAL,
    STATUS_OK,
    WRITE_SN,
)

_LOGGER = logging.getLogger(__name__)

Value = int | str | list[Any]


class AtlanticLocalError(Exception):
    """Raised when the module cannot be reached or answers badly."""


class AtlanticLocalUnsupported(AtlanticLocalError):
    """Raised when the module does not know a data-model id."""


class AtlanticLocalWriteRejected(AtlanticLocalError):
    """Raised when the module refuses a write."""


@dataclass(frozen=True)
class DeviceIdentity:
    """Static information read once from the module."""

    serial: str
    product_code: str | None
    model: str | None
    firmware: str | None
    room_name: str | None


def parse_reply(raw: str) -> dict[str, Any]:
    """Return the single data-model record carried by a command reply.

    The module wraps a JSON array, serialised as a string, inside the
    `payload` field of its JSON answer.
    """
    try:
        envelope = json.loads(raw)
        records = json.loads(envelope["payload"])
        record = records[0]
    except (ValueError, KeyError, IndexError, TypeError) as err:
        raise AtlanticLocalError(f"Unexpected reply from the module: {raw!r}") from err
    if not isinstance(record, dict):
        raise AtlanticLocalError(f"Unexpected reply from the module: {raw!r}")
    return record


def record_value(record: dict[str, Any]) -> tuple[str, Value]:
    """Return the typed key (VIU, VIS, VS, VTIS...) and value of a record."""
    for key, value in record.items():
        if key.startswith("V"):
            return key, value
    raise AtlanticLocalError(f"Record without value: {record!r}")


class AtlanticLocalApi:
    """Read and write data-model ids through `/passthrough/cmd`."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        """Initialise the client for one module."""
        self._session = session
        self._url = f"http://{host}{CMD_PATH}"
        # The module's HTTP server handles one request at a time and only
        # answers the first command of a batch.
        self._lock = asyncio.Lock()

    async def _async_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """Send one command and return the record it produced."""
        body = json.dumps([command], separators=(",", ":"))
        async with self._lock:
            try:
                async with asyncio.timeout(API_TIMEOUT):
                    response = await self._session.post(self._url, data=body)
                    response.raise_for_status()
                    raw = await response.text()
            except TimeoutError as err:
                raise AtlanticLocalError("Timeout talking to the module") from err
            except aiohttp.ClientError as err:
                raise AtlanticLocalError(f"Error talking to the module: {err}") from err
        return parse_reply(raw)

    async def async_read(self, data_id: int) -> Value:
        """Read one data-model id."""
        record = await self._async_command(
            {"CMD": CMD_READ, "SN": data_id, "ID": data_id}
        )
        if record.get("STATUS") != STATUS_OK:
            raise AtlanticLocalUnsupported(
                f"Id {data_id} not readable (error {record.get('ERROR')})"
            )
        return record_value(record)[1]

    async def async_read_many(self, data_ids: tuple[int, ...]) -> dict[int, Value]:
        """Read several ids, skipping the ones the module does not know."""
        values: dict[int, Value] = {}
        for data_id in data_ids:
            try:
                values[data_id] = await self.async_read(data_id)
            except AtlanticLocalUnsupported:
                _LOGGER.debug("Id %s not supported by the module", data_id)
        return values

    async def async_write(self, data_id: int, value: int, key: str = "VIS") -> None:
        """Write one data-model id.

        The value goes under the same typed key the module uses when reading
        that id: the generic `value` key its own web page sends is rejected
        with error 4.
        """
        record = await self._async_command(
            {"CMD": CMD_WRITE, "SN": WRITE_SN, "ID": data_id, key: value}
        )
        if record.get("CMD") != CMD_WRITE_REPLY or record.get("STATUS") != STATUS_OK:
            raise AtlanticLocalWriteRejected(
                f"Write of {value} to id {data_id} rejected "
                f"(error {record.get('ERROR')})"
            )

    async def async_identity(self) -> DeviceIdentity:
        """Read the static information describing the module."""
        serial = await self.async_read(ID_SERIAL)
        others = await self.async_read_many(
            (ID_PRODUCT_CODE, ID_MODEL, ID_FIRMWARE, ID_ROOM_NAME)
        )

        def _text(data_id: int) -> str | None:
            value = others.get(data_id)
            return str(value).strip() or None if value is not None else None

        return DeviceIdentity(
            serial=str(serial).strip(),
            product_code=_text(ID_PRODUCT_CODE),
            model=_text(ID_MODEL),
            firmware=_text(ID_FIRMWARE),
            room_name=_text(ID_ROOM_NAME),
        )
