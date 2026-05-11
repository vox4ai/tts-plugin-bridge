import pytest
from tts_plugin_bridge.skill import TTSSkill
from tts_plugin_bridge.factory import ConnectorFactory
from tts_plugin_bridge.protocol import TTSConnector, TTSRequest, TTSResponse

class MockConnector(TTSConnector):
    ENGINE_NAME = "mock"
    SUPPORTED_PARAMS = ["voice", "rate", "pitch"]
    last_request: TTSRequest | None = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
    async def synthesize(self, req: TTSRequest) -> TTSResponse:
        MockConnector.last_request = req
        return TTSResponse.ok(audio_data=b"mock_audio")
    async def synthesize_stream(self, req):
        MockConnector.last_request = req
        yield b"mock_audio_chunk"
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
async def test_skill_synthesize_with_model(mock_factory):
    MockConnector.last_request = None
    skill = TTSSkill(default_engine="mock")
    res = await skill.synthesize(text="test", model="ja-JP-KeigoNeural")

    assert res["status"] == "ok"
    assert MockConnector.last_request is not None
    assert MockConnector.last_request.model == "ja-JP-KeigoNeural", \
        f"Expected model='ja-JP-KeigoNeural', got {MockConnector.last_request.model}"
    # model は extra に入らないこと（SUPPORTED_PARAMS に含まれないため）
    assert "model" not in MockConnector.last_request.extra

@pytest.mark.asyncio
async def test_skill_play_with_model(mock_factory):
    MockConnector.last_request = None
    skill = TTSSkill(default_engine="mock")
    res = await skill.play(text="test", model="ja-JP-KeigoNeural")

    assert res["status"] == "ok"
    assert MockConnector.last_request is not None
    assert MockConnector.last_request.model == "ja-JP-KeigoNeural"

@pytest.mark.asyncio
async def test_skill_synthesize_model_not_extra(mock_factory):
    MockConnector.last_request = None
    skill = TTSSkill(default_engine="mock")
    res = await skill.synthesize(text="test", pitch=1.5, model="ja-JP-KeigoNeural")

    assert res["status"] == "ok"
    req = MockConnector.last_request
    # pitch は SUPPORTED_PARAMS にあるので extra に入る
    assert req.extra.get("pitch") == 1.5
    # model は extra ではなく model フィールド
    assert req.model == "ja-JP-KeigoNeural"
    assert "model" not in req.extra

@pytest.mark.asyncio
async def test_skill_context_manager(mock_factory):
    async with TTSSkill(default_engine="mock") as skill:
        res = await skill.synthesize(text="test")
        assert res["status"] == "ok"
        connector = await skill._get_connector("mock")
        assert not connector._closed if hasattr(connector, "_closed") else True
    
    # After exit, cache should be cleared
    assert len(skill._cache) == 0
