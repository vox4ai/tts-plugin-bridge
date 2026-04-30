import pytest
from tts_plugin_bridge.protocol import TTSRequest, TTSResponse

def test_tts_request_validation():
    # Valid request
    req = TTSRequest(text="Hello")
    assert req.text == "Hello"
    assert req.speed == 1.0
    
    # Invalid speed
    with pytest.raises(ValueError):
        TTSRequest(text="Hello", speed=10.0)

def test_tts_response_ok():
    res = TTSResponse.ok(audio_data=b"dummy")
    assert res.success is True
    assert res.audio_data == b"dummy"

def test_tts_response_fail():
    res = TTSResponse.fail(error="Error message")
    assert res.success is False
    assert res.error == "Error message"
