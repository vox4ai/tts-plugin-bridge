import base64
import argparse
import sys
import os
import asyncio
import shutil
from .protocol import TTSRequest, TTSResponse, TTSConnector, ChunkConfig
from .factory import ConnectorFactory
from typing import Optional, AsyncGenerator

class TTSSkill:
    """CodingAgent 向け TTS skill ラッパー
    
    Args:
        default_engine (str): デフォルトで使用するTTSエンジン名 (例: "piperplus")
        **engine_kwargs: コネクタ初期化時に渡される共通引数 (例: server_url="http://localhost:5000")
    """
    def __init__(self, default_engine: str = "piperplus", **engine_kwargs):
        self.default_engine = default_engine
        self._cache: dict[str, TTSConnector] = {}
        self._engine_kwargs = engine_kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _get_connector(self, engine: str) -> TTSConnector:
        if engine not in self._cache:
            kwargs = self._engine_kwargs.copy()
            self._cache[engine] = ConnectorFactory.create(engine, **kwargs)
        return self._cache[engine]

    async def synthesize(
        self,
        text: str,
        speed: float = 1.0,
        volume: Optional[float] = None,
        engine: Optional[str] = None,
        chunk: bool = False,
        chunk_config: Optional[ChunkConfig] = None,
        **kwargs
    ) -> dict:
        target = engine or self.default_engine
        connector = await self._get_connector(target)

        if not await connector.is_available():
            return {"status": "error", "message": f"{connector.name} server not reachable"}

        if chunk:
            from .chunker import HybridChunker, ChunkConfig as ChunkerConfig
            actual_config = chunk_config or ChunkerConfig()
            chunker = HybridChunker()
            chunks_to_process = chunker.chunk(text, actual_config)

            combined_audio = bytearray()
            for chunk_res in chunks_to_process:
                req = TTSRequest(
                    text=chunk_res.text, speed=speed, volume=volume,
                    extra={k: v for k, v in kwargs.items() if k in connector.get_supported_params()}
                )
                res: TTSResponse = await connector.synthesize(req)
                if not res.success:
                    return {"status": "error", "message": f"Error in chunk {chunk_res.index}: {res.error}"}
                if res.audio_data:
                    combined_audio.extend(res.audio_data)

            if not combined_audio:
                return {"status": "error", "message": "No audio data was generated"}

            return {
                "status": "ok",
                "engine": connector.name,
                "audio_base64": base64.b64encode(combined_audio).decode(),
                "message": f"TTS synthesis completed ({len(chunks_to_process)} chunks)"
            }

        req = TTSRequest(
            text=text, speed=speed, volume=volume,
            extra={k: v for k, v in kwargs.items() if k in connector.get_supported_params()}
        )
        res: TTSResponse = await connector.synthesize(req)

        if res.success:
            return {
                "status": "ok",
                "engine": connector.name,
                "audio_base64": base64.b64encode(res.audio_data).decode() if res.audio_data else None,
                "message": "TTS synthesis completed"
            }
        return {"status": "error", "message": res.error}

    async def save(
        self,
        text: str,
        speed: float = 1.0,
        volume: Optional[float] = None,
        engine: Optional[str] = None,
        chunk: bool = False,
        chunk_config: Optional[ChunkConfig] = None,
        **kwargs
    ) -> dict:
        return await self.synthesize(text, speed, volume, engine, chunk, chunk_config, **kwargs)

    async def say(
        self,
        text: str,
        speed: float = 1.0,
        volume: Optional[float] = None,
        engine: Optional[str] = None,
        **kwargs
    ) -> dict:
        return await self.play(text, speed, volume, engine, **kwargs)

    async def play(
        self,
        text: str,
        speed: float = 1.0,
        volume: Optional[float] = None,
        engine: Optional[str] = None,
        **kwargs
    ) -> dict:
        """テキストを音声合成して直接再生する（ストリーミング優先）

        Engine が synthesize_stream() を持っていればストリーミング再生（ffplay）、
        なければ synthesize() → paplay/aplay で再生する。
        """
        target = engine or self.default_engine
        connector = await self._get_connector(target)

        if not await connector.is_available():
            return {"status": "error", "message": f"{connector.name} server not reachable"}

        req = TTSRequest(
            text=text, speed=speed, volume=volume,
            extra={k: v for k, v in kwargs.items() if k in connector.get_supported_params()}
        )

        stream_method = getattr(connector, "synthesize_stream", None)
        if stream_method is not None and _has_cmd("ffplay"):
            proc = await asyncio.create_subprocess_exec(
                "ffplay", "-nodisp", "-autoexit", "-", "-loglevel", "quiet",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            async for chunk in stream_method(req):
                proc.stdin.write(chunk)
            await proc.stdin.drain()
            proc.stdin.close()
            await proc.wait()
            return {"status": "ok", "engine": connector.name, "message": "Streaming playback completed"}
        else:
            res: TTSResponse = await connector.synthesize(req)
            if not res.success:
                return {"status": "error", "message": res.error}
            if not res.audio_data:
                return {"status": "error", "message": "No audio data generated"}
            ok = await _play_audio(res.audio_data)
            if not ok:
                return {"status": "error", "message": "No audio player found (paplay / aplay)"}
            return {"status": "ok", "engine": connector.name, "message": "Playback completed"}

    async def close(self):
        for conn in self._cache.values():
            await conn.close()
        self._cache.clear()


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
    
    # list コマンド
    subparsers.add_parser('list', help='利用可能なTTSプラグインを一覧表示')
    
    # synthesize コマンド
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
    
    # play コマンド
    play_parser = subparsers.add_parser('play', help='テキストを音声合成して直接再生')
    play_parser.add_argument('text', help='合成するテキスト')
    play_parser.add_argument('--engine', '-e', help='使用するTTSエンジン (デフォルト: piperplus)')
    play_parser.add_argument('--speed', '-s', type=float, default=1.0, help='話速 (0.1-3.0, デフォルト: 1.0)')
    play_parser.add_argument('--volume', '-v', type=float, help='音量 (0.0-3.0)')
    play_parser.add_argument('--pitch', '-p', type=float, help='ピッチ補正 (エンジン依存)')
    play_parser.add_argument('--server-url', help='TTSサーバーURL (例: http://localhost:5000)')
    play_parser.add_argument('--style-id', type=int, help='AivisSpeechなど: 話者スタイルID (例: 888753760)')
    play_parser.add_argument('--model', help='音声モデル名 (edge-tts の voice など)')
    
    # test コマンド
    test_parser = subparsers.add_parser('test', help='TTS接続をテスト')
    test_parser.add_argument('--engine', '-e', help='使用するTTSエンジン (デフォルト: piperplus)')
    test_parser.add_argument('--server-url', help='TTSサーバーURL (例: http://localhost:5000)')
    test_parser.add_argument('--style-id', type=int, help='AivisSpeechなど: 話者スタイルID (例: 888753760)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # エンジンオプションを準備
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
    """tts-plugin-bridge CLI エントリーポイント"""
    return asyncio.run(_main_async())


# ── vox4ai CLI ──────────────────────────────────────────────────────────

_VOX4AI_EPILOG = """
使用例:
  vox4ai say "こんにちは"                  # テキストを読む（ストリーミング優先）
  vox4ai say "Hello" -e edgetts           # Edge TTS で読む
  vox4ai save "こんにちは" -o output.wav   # WAV ファイルに保存
  vox4ai list                              # 利用可能エンジン一覧
  vox4ai test -e aivisspeech              # 接続テスト
  vox4ai --commands                        # 使用可能なサブコマンド一覧
  vox4ai --doctor                         # 環境診断
  vox4ai --tts-plugin-list                # TTS Engine 一覧
"""

_VOX4AI_COMMANDS = {
    "say": "テキストを読み上げる（ストリーミング優先、ffplay/paplay/aplay）",
    "save": "テキストを音声ファイルに保存",
    "list": "利用可能なTTSプラグインを一覧表示",
    "test": "TTSエンジンへの接続をテスト",
}


def vox4ai_main():
    """vox4ai CLI エントリーポイント（say / save / list / test）"""
    return asyncio.run(_vox4ai_async())


async def _vox4ai_async():
    parser = argparse.ArgumentParser(
        description="vox4ai - 音声合成 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_VOX4AI_EPILOG,
        add_help=False,
    )
    parser.add_argument(
        "--commands", action="store_true",
        help="利用可能なサブコマンド一覧を表示",
    )
    parser.add_argument(
        "--doctor", action="store_true",
        help="環境の動作確認（依存コマンド・プラグイン）",
    )
    parser.add_argument(
        "--tts-plugin-list", action="store_true",
        help="利用可能なTTS Engine 一覧",
    )
    parser.add_argument("-h", "--help", action="store_true", help="ヘルプを表示")

    known, remaining = parser.parse_known_args()

    if known.help:
        parser.print_help()
        return 0

    if known.commands:
        print("利用可能なサブコマンド:")
        for name, desc in _VOX4AI_COMMANDS.items():
            print(f"  {name:8s}  {desc}")
        print()
        print("詳細: vox4ai <コマンド> --help")
        return 0

    if known.doctor:
        return await _vox4ai_doctor()

    if known.tts_plugin_list:
        return await list_engines()

    sub = parser.add_subparsers(dest="command", help="利用可能なコマンド")
    # list
    sub.add_parser("list", help="利用可能なTTSプラグインを一覧表示")
    # say
    say_parser = sub.add_parser("say", help="テキストを読み上げる（ストリーミング優先）")
    say_parser.add_argument("text", help="読み上げるテキスト")
    say_parser.add_argument("--engine", "-e", help="TTSエンジン名")
    say_parser.add_argument("--speed", "-s", type=float, default=1.0, help="話速")
    say_parser.add_argument("--volume", "-v", type=float, help="音量")
    say_parser.add_argument("--pitch", "-p", type=float, help="ピッチ補正")
    say_parser.add_argument("--server-url", help="TTSサーバーURL")
    say_parser.add_argument("--style-id", type=int, help="話者スタイルID")
    say_parser.add_argument("--model", help="音声モデル名")
    # save
    save_parser = sub.add_parser("save", help="テキストを音声ファイルに保存")
    save_parser.add_argument("text", help="合成するテキスト")
    save_parser.add_argument("--engine", "-e", help="TTSエンジン名")
    save_parser.add_argument("--speed", "-s", type=float, default=1.0, help="話速")
    save_parser.add_argument("--volume", "-v", type=float, help="音量")
    save_parser.add_argument("--pitch", "-p", type=float, help="ピッチ補正")
    save_parser.add_argument("--server-url", help="TTSサーバーURL")
    save_parser.add_argument("--style-id", type=int, help="話者スタイルID")
    save_parser.add_argument("--output", "-o", help="出力ファイルパス（省略時はBase64表示）")
    save_parser.add_argument("--play", action="store_true", help="保存後に再生")
    # test
    test_parser = sub.add_parser("test", help="TTS接続をテスト")
    test_parser.add_argument("--engine", "-e", help="TTSエンジン名")
    test_parser.add_argument("--server-url", help="TTSサーバーURL")
    test_parser.add_argument("--style-id", type=int, help="話者スタイルID")

    args = parser.parse_args(remaining)

    if not args.command:
        parser.print_help()
        return 1

    engine_kwargs = {}
    if hasattr(args, "server_url") and args.server_url:
        engine_kwargs["server_url"] = args.server_url

    if args.command == "list":
        return await list_engines()
    elif args.command == "say":
        return await play_text(
            args.text, getattr(args, "engine", None),
            args.speed, getattr(args, "volume", None),
            getattr(args, "pitch", None),
            getattr(args, "style_id", None),
            getattr(args, "model", None),
            engine_kwargs,
        )
    elif args.command == "save":
        return await synthesize_text(
            args.text, getattr(args, "engine", None),
            args.speed, getattr(args, "volume", None),
            getattr(args, "pitch", None),
            getattr(args, "style_id", None),
            getattr(args, "output", None),
            engine_kwargs, False, getattr(args, "play", False),
        )
    elif args.command == "test":
        return await test_connection(
            getattr(args, "engine", None),
            getattr(args, "style_id", None),
            engine_kwargs,
        )
    else:
        parser.print_help()
        return 1


async def _vox4ai_doctor():
    """環境診断: 依存コマンド・プラグイン導入状況を表示"""
    print("vox4ai 環境診断")
    print("=" * 40)

    # 再生コマンド
    print(f"\n[再生コマンド]")
    for cmd in ("ffplay", "paplay", "aplay"):
        found = shutil.which(cmd) is not None
        print(f"  {cmd:12s} {'✅ found' if found else '❌ not found'}")

    # 利用可能なTTSプラグイン
    print(f"\n[TTS プラグイン]")
    try:
        engines = ConnectorFactory.list_available()
        if engines:
            for eng in engines:
                print(f"  {eng:15s} ✅ registered")
        else:
            print("  (none found)")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

    # 依存パッケージ
    print(f"\n[Python パッケージ]")
    for pkg in ("tts-plugin-bridge", "edge-tts", "aiohttp", "pydantic"):
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  {pkg:20s} ✅ installed")
        except ImportError:
            print(f"  {pkg:20s} ❌ not installed")

    print()
    return 0


async def list_engines():
    """利用可能なエンジンを一覧表示"""
    try:
        engines = ConnectorFactory.list_available()
        if engines:
            print("利用可能なTTSプラグイン:")
            for engine in engines:
                print(f"  - {engine}")
        else:
            print("利用可能なTTSプラグインが見つかりません。")
            print("プラグインをインストールするには: uv add tts-plugin-<エンジン名>")
    except Exception as e:
        print(f"エラー: {e}")
        return 1
    return 0


def _has_cmd(name: str) -> bool:
    return shutil.which(name) is not None

def _find_player(for_stream: bool = False) -> Optional[str]:
    if for_stream and _has_cmd("ffplay"):
        return "ffplay"
    if _has_cmd("paplay"):
        return "paplay"
    if _has_cmd("aplay"):
        return "aplay"
    return None

async def _play_audio(data: bytes) -> bool:
    tmp = "/tmp/_tts_play.wav"
    with open(tmp, "wb") as f:
        f.write(data)
    try:
        player = None
        if _has_cmd("paplay"):
            player = "paplay"
        elif _has_cmd("aplay"):
            player = "aplay"
        if not player:
            return False
        proc = await asyncio.create_subprocess_exec(
            player, tmp,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


async def synthesize_text(text: str, engine: Optional[str], speed: float, volume: Optional[float], 
                         pitch: Optional[float], style_id: Optional[int], output: Optional[str],
                         engine_kwargs: dict, chunk: bool = False, play: bool = False,
                         chunk_config: Optional[ChunkConfig] = None):
    """テキストを音声合成"""
    try:
        async with TTSSkill(default_engine=engine or "piperplus", **engine_kwargs) as skill:
            kwargs = {}
            if volume is not None:
                kwargs['volume'] = volume
            if pitch is not None:
                kwargs['pitch'] = pitch
            if style_id is not None:
                kwargs['style_id'] = style_id
            if chunk:
                kwargs['chunk'] = True
                kwargs['chunk_config'] = chunk_config
                
            result = await skill.synthesize(
                text=text,
                speed=speed,
                engine=engine,
                **kwargs
            )
            
            if result["status"] == "ok":
                import base64
                audio_data = base64.b64decode(result["audio_base64"])
                if output:
                    with open(output, 'wb') as f:
                        f.write(audio_data)
                    print(f"音声データを {output} に保存しました。")
                    print(f"エンジン: {result['engine']}")
                    print(f"メッセージ: {result['message']}")
                elif play:
                    ok = await _play_audio(audio_data)
                    if not ok:
                        print("エラー: 再生に使えるコマンド (paplay / aplay) が見つかりません。")
                        return 1
                    print(f"✅ 再生完了 (エンジン: {result['engine']})")
                else:
                    # Base64を表示
                    print(f"エンジン: {result['engine']}")
                    print(f"メッセージ: {result['message']}")
                    print(f"音声データ (Base64): {result['audio_base64'][:100]}..." if result['audio_base64'] else "音声データ: None")
                    if len(result['audio_base64'] or '') > 100:
                        print(f"... (全長: {len(result['audio_base64'] or '')} 文字)")
            else:
                print(f"エラー: {result['message']}")
                return 1
    except Exception as e:
        print(f"エラー: {e}")
        return 1
    return 0


async def play_text(text: str, engine: Optional[str], speed: float, volume: Optional[float],
                    pitch: Optional[float], style_id: Optional[int], model: Optional[str],
                    engine_kwargs: dict):
    try:
        async with TTSSkill(default_engine=engine or "piperplus", **engine_kwargs) as skill:
            kwargs = {}
            if volume is not None:
                kwargs['volume'] = volume
            if pitch is not None:
                kwargs['pitch'] = pitch
            if style_id is not None:
                kwargs['style_id'] = style_id
            if model is not None:
                kwargs['model'] = model
            result = await skill.play(
                text=text,
                speed=speed,
                engine=engine,
                **kwargs
            )
            if result["status"] == "ok":
                print(f"✅ {result['message']} (エンジン: {result['engine']})")
            else:
                print(f"エラー: {result['message']}")
                return 1
    except Exception as e:
        print(f"エラー: {e}")
        return 1
    return 0


async def test_connection(engine: Optional[str], style_id: Optional[int], engine_kwargs: dict):
    """TTS接続をテスト"""
    try:
        async with TTSSkill(default_engine=engine or "piperplus", **engine_kwargs) as skill:
            kwargs = {}
            if style_id is not None:
                kwargs['style_id'] = style_id
            result = await skill.synthesize(
                text="テスト",
                speed=1.0,
                engine=engine,
                **kwargs
            )
            
            if result["status"] == "ok":
                print("✅ 接続成功!")
                print(f"エンジン: {result['engine']}")
                print(f"メッセージ: {result['message']}")
            else:
                print(f"❌ 接続失敗: {result['message']}")
                return 1
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
