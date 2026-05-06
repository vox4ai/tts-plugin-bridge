from abc import ABC, abstractmethod
from typing import ClassVar, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum

class ChunkStrategy(Enum):
    SENTENCE = "sentence"      # 句点(。！？)で分割
    CHARACTER_COUNT = "char"   # 文字数で分割
    HYBRID = "hybrid"          # 原則sentence、max_chars超えりでchar分割
    PAUSE_MARKERS = "pause"    # 「、」など一時停止マーカーで分割

@dataclass
class ChunkConfig:
    strategy: ChunkStrategy = ChunkStrategy.HYBRID
    max_chars: int = 100       # HYBRID/CHARACTER_COUNT時
    max_duration_sec: float = 30.0  # 目標最長時間
    min_chars: int = 10        # 最小文字数（短すぎる分割を防ぐ）
    preserve_punctuation: bool = True  # 句読点を保持するか

@dataclass
class ChunkResult:
    """分割されたテキストの情報を保持するクラス"""
    text: str
    index: int
    char_count: int
    is_partial: bool = False   # 文の途中での分割
    original_sentence: str = ""  # 分割元の文（HYBRID時）

class TTSRequest(BaseModel):
    """全エンジン共通のリクエストモデル"""
    text: str = Field(..., min_length=1, description="合成テキスト")
    speed: float = Field(default=1.0, ge=0.1, le=3.0, description="話速: 1.0=標準, >1.0=速い")
    pitch: Optional[float] = Field(default=None, description="ピッチ補正（エンジン依存）")
    volume: Optional[float] = Field(default=1.0, ge=0.0, le=3.0, description="音量倍率")
    model: Optional[str] = Field(default=None, description="エンジン固有モデル名")
    output_format: str = Field(default="wav", description="出力フォーマット")
    chunk: bool = Field(default=False, description="テキスト分割を有効にするか")
    chunk_config: Optional[ChunkConfig] = Field(default=None, description="分割の設定")
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
