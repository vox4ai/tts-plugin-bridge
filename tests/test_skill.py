import pytest
from tts_plugin_bridge.skill import TTSSkill
from tts_plugin_bridge.factory import ConnectorFactory
from tts_plugin_bridge.protocol import TTSConnector, TTSRequest, TTSResponse

class MockConnector(TTSConnector):
    ENGINE_NAME = "mock"
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    async def synthesize(self, req: TTSRequest) -> TTSResponse:
        return TTSResponse.ok(audio_data=b"mock_audio")
    async def is_available(self) -> bool:
        return True

@pytest.fixture
def mock_factory():
    ConnectorFactory._registry["mock"] = MockConnector
    yield
    if "mock" in ConnectorFactory._registry:
        del ConnectorFactory._registry["mock"]

@pytest.mark.asyncio
async def test_skill_synthesize(mock_factory):
    skill = TTSSkill(default_engine="mock")
    res = await skill.synthesize(text="test")
    
    assert res["status"] == "ok"
    assert res["engine"] == "mock"
    assert "audio_base64" in res
    assert res["message"] == "TTS synthesis completed"

@pytest.mark.asyncio
async def test_skill_unavailable(mock_factory):
    class UnavailableConnector(MockConnector):
        async def is_available(self) -> bool:
            return False
    
    ConnectorFactory._registry["mock"] = UnavailableConnector
    skill = TTSSkill(default_engine="mock")
    res = await skill.synthesize(text="test")
    
    assert res["status"] == "error"
    assert "not reachable" in res["message"]

@pytest.mark.asyncio
async def test_skill_context_manager(mock_factory):
    async with TTSSkill(default_engine="mock") as skill:
        res = await skill.synthesize(text="test")
        assert res["status"] == "ok"
        connector = await skill._get_connector("mock")
        assert not connector._closed if hasattr(connector, "_closed") else True
    
    # After exit, cache should be cleared
    assert len(skill._cache) == 0
