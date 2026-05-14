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
