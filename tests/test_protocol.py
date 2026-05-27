import pytest
from pydantic import ValidationError
from tts_plugin_bridge.protocol import (
    TTSRequest,
    TTSResponse,
    ChunkConfig,
    ChunkStrategy,
)


class TestTTSRequest:
    def test_valid_defaults(self):
        req = TTSRequest(text="Hello")
        assert req.text == "Hello"
        assert req.speed == 1.0
        assert req.pitch is None
        assert req.volume == 1.0
        assert req.model is None
        assert req.output_format == "wav"
        assert req.chunk is False
        assert req.chunk_config is None
        assert req.extra == {}

    def test_minimal_text(self):
        req = TTSRequest(text="a")
        assert req.text == "a"

    def test_empty_text_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(text="")

    def test_speed_at_boundaries(self):
        # Lower boundary
        req = TTSRequest(text="test", speed=0.1)
        assert req.speed == 0.1
        # Upper boundary
        req = TTSRequest(text="test", speed=3.0)
        assert req.speed == 3.0

    def test_speed_below_minimum_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(text="test", speed=0.0)

    def test_speed_above_maximum_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(text="test", speed=3.1)

    def test_volume_at_boundaries(self):
        req = TTSRequest(text="test", volume=0.0)
        assert req.volume == 0.0
        req = TTSRequest(text="test", volume=3.0)
        assert req.volume == 3.0

    def test_volume_negative_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(text="test", volume=-0.1)

    def test_chunk_config_propagation(self):
        config = ChunkConfig(strategy=ChunkStrategy.SENTENCE, max_chars=50)
        req = TTSRequest(text="test", chunk=True, chunk_config=config)
        assert req.chunk_config is config
        assert req.chunk_config.strategy == ChunkStrategy.SENTENCE

    def test_extra_params(self):
        req = TTSRequest(text="test", extra={"style_id": 123, "custom": "val"})
        assert req.extra["style_id"] == 123
        assert req.extra["custom"] == "val"

    def test_model_field(self):
        req = TTSRequest(text="test", model="ja-JP-KeigoNeural")
        assert req.model == "ja-JP-KeigoNeural"
        assert "model" not in req.extra


class TestTTSResponse:
    def test_ok(self):
        res = TTSResponse.ok(audio_data=b"dummy")
        assert res.success is True
        assert res.audio_data == b"dummy"
        assert res.error is None

    def test_ok_with_metadata(self):
        res = TTSResponse.ok(
            audio_data=b"data", duration_sec=2.5, metadata={"format": "wav"}
        )
        assert res.duration_sec == 2.5
        assert res.metadata["format"] == "wav"

    def test_fail(self):
        res = TTSResponse.fail(error="Error message")
        assert res.success is False
        assert res.error == "Error message"
        assert res.audio_data is None

    def test_fail_with_metadata(self):
        res = TTSResponse.fail(error="fail")
        assert res.success is False
        assert res.error == "fail"
        assert res.audio_data is None
