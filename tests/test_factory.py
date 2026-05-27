from typing import AsyncIterator

import pytest
from tts_plugin_bridge.protocol import TTSConnector, TTSRequest, TTSResponse
from tts_plugin_bridge.factory import ConnectorFactory


class MockConnector(TTSConnector):
    ENGINE_NAME = "mock"

    async def synthesize(self, req: TTSRequest) -> TTSResponse:
        return TTSResponse.ok(audio_data=b"mock")

    async def synthesize_stream(self, req: TTSRequest) -> AsyncIterator[bytes]:
        yield b"mock"

    async def is_available(self) -> bool:
        return True

    async def close(self):
        pass


def test_factory_registration():
    # Manually register for testing
    ConnectorFactory._registry["mock"] = MockConnector

    assert "mock" in ConnectorFactory.list_available()

    connector = ConnectorFactory.create("mock")
    assert isinstance(connector, MockConnector)
    assert connector.name == "mock"


def test_factory_not_found():
    with pytest.raises(ValueError, match="Plugin 'invalid' not found"):
        ConnectorFactory.create("invalid")


def test_factory_case_insensitive():
    ConnectorFactory._registry["mock"] = MockConnector
    connector = ConnectorFactory.create("Mock")
    assert isinstance(connector, MockConnector)


def test_factory_duplicate_skip():
    ConnectorFactory._registry.clear()
    ConnectorFactory._discovered = False

    # Register first
    ConnectorFactory._registry["mock"] = MockConnector
    # Register again — should warn but not raise
    old_len = len(ConnectorFactory._registry)
    ConnectorFactory._registry["mock"] = MockConnector
    assert len(ConnectorFactory._registry) == old_len


def test_factory_create_with_kwargs():
    class ConnectorWithArgs(MockConnector):
        def __init__(self, **kwargs):
            self.received = kwargs

    ConnectorFactory._registry["withargs"] = ConnectorWithArgs
    conn = ConnectorFactory.create("withargs", server_url="http://test", timeout=10)
    assert conn.received["server_url"] == "http://test"
    assert conn.received["timeout"] == 10
