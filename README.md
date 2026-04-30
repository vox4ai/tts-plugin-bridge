# tts-plugin-bridge

TTSエンジンのプラグイン化・動的発見・Agent連携を可能にするコアフレームワークです。

## ✨ 特徴
- 🔌 **Entry Points による自動発見**: `uv add tts-plugin-xxx` するだけで自動的にブリッジへ登録
- 🔀 **エンジン非依存**: コアパッケージは特定のTTSに依存せず、軽量で安定
- 🤖 **Agent 最適化**: `TTSSkill` クラスで非同期呼び出し・パラメータ統一・Base64出力を標準提供
- 🛡️ **型安全**: Pydantic ベースのリクエスト/レスポンスでバリデーション自動実行

## 📦 インストール
```bash
uv add tts-plugin-bridge
```

## 🧩 使い方
```python
from tts_plugin_bridge import TTSSkill

skill = TTSSkill(default_engine="piperplus", server_url="http://localhost:5000")

res = await skill.synthesize(
    text="こんにちは、プラグインブリッジのテストです。",
    speed=0.9,
    volume=1.2
)
print(res["audio_base64"][:50], "...")  # Base64エンコード済みWAV
```

### CLI コマンドライン使用方法
インストール後、`tts-plugin-bridge` コマンドが利用可能になります。

#### 利用可能なプラグイン一覧表示
```bash
tts-plugin-bridge list
```

#### テキストから音声合成
```bash
tts-plugin-bridge synthesize "こんにちは、世界"
```

#### オプション付き音声合成
```bash
tts-plugin-bridge synthesize "こんにちは、世界" \
    --engine piperplus \
    --speed 1.2 \
    --volume 1.0 \
    --output ./output.wav
```

#### TTS接続テスト
```bash
tts-plugin-bridge test
tts-plugin-bridge test --engine piperplus --server-url http://localhost:5000
```

#### ヘルプ表示
```bash
tts-plugin-bridge --help
tts-plugin-bridge synthesize --help
```

## 🔧 プラグイン開発者向け
独自のTTSエンジンをプラグイン化するには、`pyproject.toml` にエントリーポイントを定義するだけです。
詳細は各プラグインリポジトリのドキュメントを参照してください。

## 📜 ライセンス
MIT License
