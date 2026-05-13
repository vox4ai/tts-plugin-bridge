from .protocol import TTSRequest, TTSResponse, TTSConnector
from .factory import ConnectorFactory

__all__ = ["TTSRequest", "TTSResponse", "TTSConnector", "ConnectorFactory", "TTSSkill"]


def __getattr__(name):
    if name == "TTSSkill":
        import vox4ai_skill_lib  # noqa: F811
        return vox4ai_skill_lib.TTSSkill
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
