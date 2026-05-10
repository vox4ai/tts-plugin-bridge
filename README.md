# tts-plugin-bridge

TTSエンジンのプラグイン化・動的発見・Agent連携を可能にするコアフレームワークです。

## ✨ 特徴
- 🔌 **Entry Points による自動発見**: `uv add tts-plugin-xxx` するだけで自動的にブリッジへ登録
- 🔀 **エンジン非依存**: コアパッケージは特定のTTSに依存せず、軽量で安定
- 🤖 **Agent 最適化**: `TTSSkill` クラスで非同期呼び出し・パラメータ統一・Base64出力を標準提供
- 🛡️ **型安全**: Pydantic ベースのリクエスト/レスポンスでバリデーション自動実行
- 🎤 **vox4ai CLI**: 統一インターフェースの `vox4ai` コマンドを同梱（say/save/list/test + 環境診断）

## 📦 インストール
```bash
uv add tts-plugin-bridge
```

## 🧩 使い方（Python API）

```python
from tts_plugin_bridge import TTSSkill

async with TTSSkill(default_engine="edgetts") as skill:
    # 音声ファイルに保存（save は synthesize の alias）
    res = await skill.save(
        text="こんにちは",
        speed=1.2,
        volume=1.0,
    )
    with open("output.mp3", "wb") as f:
        f.write(base64.b64decode(res["audio_base64"]))

    # 直接再生（say は play の alias）
    res = await skill.say(
        text="こんにちは",
        model="ja-JP-KeitaNeural",
    )
```

### メソッド一覧

| メソッド | alias | 戻り値 | 用途 |
|----------|-------|--------|------|
| `synthesize()` | `save()` | `dict` (Base64) | 音声合成してBase64として返す |
| `play()` | `say()` | `dict` | 直接再生（ストリーミング優先→全取得後再生） |
| `close()` | - | `None` | 全コネクタのリソース解放 |

- `say()` / `play()` は Engine が `synthesize_stream()` を実装していれば ffplay でストリーミング、なければ synthesize → paplay/aplay で再生
- Engine ごとに再生方式が異なるが、ユーザーは `say()` という同じインターフェースで使える

---

## 🎤 vox4ai CLI

`vox4ai` は `tts-plugin-bridge` に同梱される統合TTS操作コマンドです。
サブコマンドで直感的に操作できます。

```
vox4ai say "こんにちは"
vox4ai save "こんにちは" -o output.wav
vox4ai list
vox4ai test -e aivisspeech
```

### グローバルオプション

```bash
vox4ai --commands              # 利用可能なサブコマンド一覧
vox4ai --doctor                # 環境診断（再生コマンド・プラグイン・パッケージ）
vox4ai --tts-plugin-list       # TTS Engine 一覧（listと同じ）
```

#### `vox4ai --doctor` で確認できる項目
- 再生コマンド: ffplay / paplay / aplay の有無
- 登録TTSプラグイン一覧
- Python パッケージ導入状況

### サブコマンド

#### `say` — テキストを読み上げる（ストリーミング再生優先）

```bash
vox4ai say "こんにちは"                        # デフォルトエンジン
vox4ai say "Hello" -e edgetts                 # Edge TTS（ffplayストリーミング）
vox4ai say "こんにちは" -e aivisspeech          # AivisSpeech
  --server-url http://localhost:10101
  --style-id 888753760
vox4ai say "Hello" -e edgetts                 # 話速・声指定
  --speed 1.5
  --model en-US-AndrewNeural
```

#### `save` — テキストを音声ファイルに保存

```bash
vox4ai save "こんにちは" -o hello.wav           # WAV保存
vox4ai save "こんにちは" -e edgetts -o out.mp3  # Edge TTS（MP3）
vox4ai save "こんにちは" -e aivisspeech          # AivisSpeech
  --server-url http://localhost:10101
  --style-id 888753760
  --output hello.wav
vox4ai save "こんにちは" --play                 # 保存後に再生
```

#### `list` — 利用可能なTTSプラグイン一覧

```bash
vox4ai list
```

#### `test` — TTSエンジン接続テスト

```bash
vox4ai test -e edgetts
vox4ai test -e aivisspeech --server-url http://localhost:10101 --style-id 888753760
```

### ヘルプ

```bash
vox4ai --help            # 全体ヘルプ
vox4ai say --help        # say サブコマンドのヘルプ
vox4ai save --help       # save サブコマンドのヘルプ
```

---

### tts-plugin-bridge CLI（後方互換）

`tts-plugin-bridge` コマンドも引き続き利用可能です。

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

# AivisSpeech Engine の場合（--style-id が必須）
tts-plugin-bridge synthesize "こんにちは" \
    --engine aivisspeech \
    --server-url http://localhost:10101 \
    --style-id 888753760 \
    --output hello.wav

# 直接再生（Linux の場合 paplay / aplay が必要）
tts-plugin-bridge synthesize "こんにちは" \
    --engine aivisspeech \
    --server-url http://localhost:10101 \
    --style-id 888753760 \
    --play
```

#### 直接再生（play）
Edge TTS のようにストリーミング再生に対応したエンジンでは `ffplay` 経由で即時再生します。
その他のエンジンは `paplay` / `aplay` で全取得後に再生します。

```bash
# デフォルトエンジンで再生
tts-plugin-bridge play "こんにちは、世界"

# Edge TTS（ストリーミング再生）
tts-plugin-bridge play "こんにちは" -e edgetts

# 話速・音量・声指定
tts-plugin-bridge play "Hello" -e edgetts --speed 1.5 --model en-US-AndrewNeural

# AivisSpeech Engine
tts-plugin-bridge play "こんにちは" --engine aivisspeech --server-url http://localhost:10101 --style-id 888753760
```

#### TTS接続テスト
```bash
tts-plugin-bridge test
tts-plugin-bridge test --engine piperplus --server-url http://localhost:5000

# AivisSpeech Engine の場合
tts-plugin-bridge test --engine aivisspeech --server-url http://localhost:10101 --style-id 888753760
```

#### ヘルプ表示
```bash
tts-plugin-bridge --help
tts-plugin-bridge synthesize --help
```

## 🔧 プラグイン開発者向け
独自のTTSエンジンをプラグイン化するには、`pyproject.toml` にエントリーポイントを定義するだけです。
詳細は各プラグインリポジトリのドキュメントを参照してください。

## 検証環境

- **OS**: Windows 11 + WSL2 (Ubuntu)
- **確認日**: 2026-05-09
- **確認プラグイン**: tts-plugin-aivisspeech (v1.2.0), tts-plugin-edgetts (edge-tts v7.2.8), tts-plugin-kokoro
- **確認内容**:
  - `vox4ai say` / `save` / `list` / `test` / `--doctor` / `--commands` 全動作確認
  - `tts-plugin-bridge` CLI 後方互換維持
  - AivisSpeech: synthesize --style-id → WAV出力 (44100Hz), play → paplay再生
  - Edge TTS: play → ffplay ストリーミング再生, synthesize → MP3出力
  - 全ユニットテストパス: bridge 11件, aivisspeech 16件, edgetts 22件

## 📜 ライセンス
MIT License
