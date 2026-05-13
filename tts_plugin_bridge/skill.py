import argparse
import asyncio

from vox4ai_skill_lib import TTSSkill  # noqa: F401 — re-exported for backward compat
from vox4ai_skill_lib.api import list_engines, synthesize_text, play_text, test_connection



async def _main_async():
    """非同期CLI エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="TTSプラグインブリッジ CLI - TTSエンジンの動的発見・管理・Agent連携",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  tts-plugin-bridge list                    # 利用可能なプラグインを一覧表示
  tts-plugin-bridge synthesize "こんにちは"   # テキストを音声合成
  tts-plugin-bridge test                    # デフォルトエンジンでテスト合成
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')

    subparsers.add_parser('list', help='利用可能なTTSプラグインを一覧表示')

    synth_parser = subparsers.add_parser('synthesize', help='テキストを音声合成')
    synth_parser.add_argument('text', help='合成するテキスト')
    synth_parser.add_argument('--engine', '-e', help='使用するTTSエンジン (デフォルト: piperplus)')
    synth_parser.add_argument('--speed', '-s', type=float, default=1.0, help='話速 (0.1-3.0, デフォルト: 1.0)')
    synth_parser.add_argument('--volume', '-v', type=float, help='音量 (0.0-3.0)')
    synth_parser.add_argument('--pitch', '-p', type=float, help='ピッチ補正 (エンジン依存)')
    synth_parser.add_argument('--output', '-o', help='出力ファイルパス (指定しない場合はBase64を表示)')
    synth_parser.add_argument('--play', action='store_true', help='音声を直接再生する (paplay/aplay)')
    synth_parser.add_argument('--server-url', help='TTSサーバーURL (例: http://localhost:5000)')
    synth_parser.add_argument('--style-id', type=int, help='AivisSpeechなど: 話者スタイルID (例: 888753760)')
    synth_parser.add_argument('--chunk', action='store_true', help='テキスト分割を有効にする')

    play_parser = subparsers.add_parser('play', help='テキストを音声合成して直接再生')
    play_parser.add_argument('text', help='合成するテキスト')
    play_parser.add_argument('--engine', '-e', help='使用するTTSエンジン (デフォルト: piperplus)')
    play_parser.add_argument('--speed', '-s', type=float, default=1.0, help='話速 (0.1-3.0, デフォルト: 1.0)')
    play_parser.add_argument('--volume', '-v', type=float, help='音量 (0.0-3.0)')
    play_parser.add_argument('--pitch', '-p', type=float, help='ピッチ補正 (エンジン依存)')
    play_parser.add_argument('--server-url', help='TTSサーバーURL (例: http://localhost:5000)')
    play_parser.add_argument('--style-id', type=int, help='AivisSpeechなど: 話者スタイルID (例: 888753760)')
    play_parser.add_argument('--model', help='音声モデル名 (edge-tts の voice など)')

    test_parser = subparsers.add_parser('test', help='TTS接続をテスト')
    test_parser.add_argument('--engine', '-e', help='使用するTTSエンジン (デフォルト: piperplus)')
    test_parser.add_argument('--server-url', help='TTSサーバーURL (例: http://localhost:5000)')
    test_parser.add_argument('--style-id', type=int, help='AivisSpeechなど: 話者スタイルID (例: 888753760)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    engine_kwargs = {}
    if hasattr(args, 'server_url') and args.server_url:
        engine_kwargs['server_url'] = args.server_url

    if args.command == 'list':
        return await list_engines()
    elif args.command == 'synthesize':
        return await synthesize_text(args.text, getattr(args, 'engine', None), args.speed, getattr(args, 'volume', None), getattr(args, 'pitch', None), getattr(args, 'style_id', None), getattr(args, 'output', None), engine_kwargs, args.chunk, getattr(args, 'play', False))
    elif args.command == 'play':
        return await play_text(args.text, getattr(args, 'engine', None), args.speed, getattr(args, 'volume', None), getattr(args, 'pitch', None), getattr(args, 'style_id', None), getattr(args, 'model', None), engine_kwargs)
    elif args.command == 'test':
        return await test_connection(getattr(args, 'engine', None), getattr(args, 'style_id', None), engine_kwargs)
    else:
        parser.print_help()
        return 1


def main():
    return asyncio.run(_main_async())