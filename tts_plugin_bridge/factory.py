import importlib.metadata
from typing import Type, Dict
from .protocol import TTSConnector


class ConnectorFactory:
    _registry: Dict[str, Type[TTSConnector]] = {}
    _discovered = False

    @classmethod
    def _discover(cls) -> None:
        if cls._discovered:
            return

        eps = importlib.metadata.entry_points(group="tts_bridge.connectors")

        for ep in eps:
            try:
                connector_cls = ep.load()
                name = getattr(connector_cls, "ENGINE_NAME", ep.name)
                if name in cls._registry:
                    print(
                        f"⚠️ Warning: Connector '{name}' already registered. Skipping {ep.value}"
                    )
                    continue
                cls._registry[name] = connector_cls
            except Exception as e:
                print(f"❌ Failed to load plugin {ep.value}: {e}")

        cls._discovered = True

    @classmethod
    def list_available(cls) -> list[str]:
        cls._discover()
        return list(cls._registry.keys())

    @classmethod
    def create(cls, engine: str, **kwargs) -> TTSConnector:
        cls._discover()
        connector_cls = cls._registry.get(engine.lower())
        if not connector_cls:
            available = ", ".join(cls.list_available()) or "none"
            raise ValueError(
                f"TTS Plugin '{engine}' not found. \n"
                f"Available engines: {available}\n"
                f"💡 To install, run: uv add tts-plugin-{engine}"
            )
        return connector_cls(**kwargs)
