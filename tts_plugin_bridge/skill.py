import base64
import argparse
import sys
import asyncio
from .protocol import TTSRequest, TTSResponse, TTSConnector, ChunkConfig
from .factory import ConnectorFactory
from typing import Optional

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
    synth_parser.add_argument('--server-url', help='TTSサーバーURL (例: http://localhost:5000)')
    synth_parser.add_argument('--chunk', action='store_true', help='テキスト分割を有効にする')
    
    # test コマンド
    test_parser = subparsers.add_parser('test', help='TTS接続をテスト')
    test_parser.add_argument('--engine', '-e', help='使用するTTSエンジン (デフォルト: piperplus)')
    test_parser.add_argument('--server-url', help='TTSサーバーURL (例: http://localhost:5000)')
    
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
        return await synthesize_text(args.text, getattr(args, 'engine', None), args.speed, getattr(args, 'volume', None), getattr(args, 'pitch', None), getattr(args, 'output', None), engine_kwargs, args.chunk)
    elif args.command == 'test':
        return await test_connection(getattr(args, 'engine', None), engine_kwargs)
    else:
        parser.print_help()
        return 1


def main():
    """CLI エントリーポイント（同期ラッパー）"""
    return asyncio.run(_main_async())


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


async def synthesize_text(text: str, engine: Optional[str], speed: float, volume: Optional[float], 
                         pitch: Optional[float], output: Optional[str], engine_kwargs: dict, chunk: bool = False, chunk_config: Optional[ChunkConfig] = None):
    """テキストを音声合成"""
    try:
        async with TTSSkill(default_engine=engine or "piperplus", **engine_kwargs) as skill:
            kwargs = {}
            if volume is not None:
                kwargs['volume'] = volume
            if pitch is not None:
                kwargs['pitch'] = pitch
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
                if output:
                    # Base64をデコードしてファイルに保存
                    import base64
                    audio_data = base64.b64decode(result["audio_base64"])
                    with open(output, 'wb') as f:
                        f.write(audio_data)
                    print(f"音声データを {output} に保存しました。")
                    print(f"エンジン: {result['engine']}")
                    print(f"メッセージ: {result['message']}")
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


async def test_connection(engine: Optional[str], engine_kwargs: dict):
    """TTS接続をテスト"""
    try:
        async with TTSSkill(default_engine=engine or "piperplus", **engine_kwargs) as skill:
            # 簡単なテキストで合成を試みる
            result = await skill.synthesize(
                text="テスト",
                speed=1.0,
                engine=engine
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
