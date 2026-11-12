"""Tests for the local API client."""

import pytest

from custom_components.atlantic_local.api import (
    AtlanticLocalApi,
    AtlanticLocalError,
    AtlanticLocalUnsupported,
    AtlanticLocalWriteRejected,
    parse_reply,
)
from tests.fake_module import FakeModule

REAL_REPLY = (
    '{"message":"Post Action Received","payload":"[{\\"CMD\\":2,\\"SN\\":117,'
    '\\"ID\\":117,\\"VIU\\":249,\\"STATUS\\":2}]","success":true}'
)


def test_parse_reply_unwraps_the_payload_string():
    assert parse_reply(REAL_REPLY) == {
        "CMD": 2,
        "SN": 117,
        "ID": 117,
        "VIU": 249,
        "STATUS": 2,
    }


def test_parse_reply_rejects_garbage():
    with pytest.raises(AtlanticLocalError):
        parse_reply("404 File not found.")


async def test_read_returns_the_typed_value():
    api = AtlanticLocalApi(FakeModule(), "192.0.2.1")
    assert await api.async_read(4118) == 2000
    assert await api.async_read(51) == "DORIS 2000W BLC"


async def test_read_unknown_id_raises_unsupported():
    api = AtlanticLocalApi(FakeModule(), "192.0.2.1")
    with pytest.raises(AtlanticLocalUnsupported):
        await api.async_read(40)


async def test_read_many_skips_unknown_ids():
    api = AtlanticLocalApi(FakeModule(), "192.0.2.1")
    assert await api.async_read_many((4118, 40)) == {4118: 2000}


async def test_write_sends_the_typed_key():
    module = FakeModule()
    api = AtlanticLocalApi(module, "192.0.2.1")
    await api.async_write(4118, 1900)
    assert module.requests[-1] == {"CMD": 3, "SN": 13, "ID": 4118, "VIS": 1900}
    assert await api.async_read(4118) == 1900


async def test_rejected_write_raises():
    module = FakeModule()
    api = AtlanticLocalApi(module, "192.0.2.1")
    with pytest.raises(AtlanticLocalWriteRejected):
        await api.async_write(4118, 1900, key="value")


async def test_network_error_is_wrapped():
    module = FakeModule()
    module.fail = True
    api = AtlanticLocalApi(module, "192.0.2.1")
    with pytest.raises(AtlanticLocalError):
        await api.async_read(4118)


async def test_identity():
    api = AtlanticLocalApi(FakeModule(), "192.0.2.1")
    identity = await api.async_identity()
    assert identity.serial == "100000000001"
    assert identity.model == "DORIS 2000W BLC"
    assert identity.product_code == "TRI TD1W"
    assert identity.firmware == "v1.5.2"
    assert identity.room_name == "Salle de bain"
