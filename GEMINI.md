# tts-plugin-bridge

TTSエンジンのプラグイン化・動的発見・Agent連携を可能にするコアフレームワークです。

## 🛠 概要
- **役割**: TTSエンジン間の共通インターフェースを提供し、プラグインの動的発見（Entry Points）と統一された操作（CLI/API）を実現する。
- **主要機能**:
    - `TTSSkill` クラスによる非同期呼び出し、パラメータ（speed, volume, model等）の統一。
    - `vox4ai` CLI (say, save, list, test, --doctor) による統合操作。
    - Pydantic による型安全なリクエスト/レスポンス。

## 📦 依存関係
- `pydantic`, `pydantic-settings`
- `tts-plugin-aivisspeech` (development)
- `tts-plugin-edgetts` (development)
- `vox4ai-skill-lib` (development)

## 🚀 開発・実行
- **パッケージ管理**: `uv`
- **テスト**: `pytest` (asyncio対応)
- **リンター**: `ruff`

## 🔗 関連リポジトリ
- `repos/vox4ai`: 統合CLI
- `repos/vox4ai-skill-lib`: Python APIライブラリ
- 各種 `tts-plugin-*`: 各種TTSエンジンプラグイン
