from abc import ABC, abstractmethod
from typing import ClassVar, Optional
from pydantic import BaseModel, Field

class TTSRequest(BaseModel):
    """全エンジン共通のリクエストモデル"""
    text: str = Field(..., min_length=1, description="合成テキスト")
    speed: float = Field(default=1.0, ge=0.1, le=3.0, description="話速: 1.0=標準, >1.0=速い")
    pitch: Optional[float] = Field(default=None, description="ピッチ補正（エンジン依存）")
    volume: Optional[float] = Field(default=1.0, ge=0.0, le=3.0, description="音量倍率")
    model: Optional[str] = Field(default=None, description="エンジン固有モデル名")
    output_format: str = Field(default="wav", description="出力フォーマット")
    extra: dict = Field(default_factory=dict, description="エンジン固有パラメータ")

class TTSResponse(BaseModel):
    """全エンジン共通のレスポンスモデル"""
    success: bool
    audio_data: Optional[bytes] = None
    file_path: Optional[str] = None
    duration_sec: Optional[float] = None
    error: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def ok(cls, audio_data: bytes, **kwargs) -> 'TTSResponse':
        return cls(success=True, audio_data=audio_data, **kwargs)

    @classmethod
    def fail(cls, error: str, **kwargs) -> 'TTSResponse':
        return cls(success=False, error=error, **kwargs)

class TTSConnector(ABC):
    """TTSエンジン共通インターフェース"""
    ENGINE_NAME: ClassVar[str] = "unknown"
    SUPPORTED_PARAMS: ClassVar[list[str]] = []

    @property
    def name(self) -> str:
        return self.ENGINE_NAME

    @abstractmethod
    async def synthesize(self, req: TTSRequest) -> TTSResponse:
        """音声合成を実行"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """エンジンサーバーが利用可能かチェック"""
        pass

    def get_supported_params(self) -> list[str]:
        return self.SUPPORTED_PARAMS.copy()

    async def close(self):
        """リソース解放（オプション）"""
        pass
