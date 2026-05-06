import pytest
from tts_plugin_bridge.chunker import (
    SentenceChunker,
    CharacterCountChunker,
    HybridChunker,
)
from tts_plugin_bridge.protocol import ChunkConfig, ChunkStrategy

def test_sentence_chunker():
    chunker = SentenceChunker()
    config = ChunkConfig(strategy=ChunkStrategy.SENTENCE)
    
    # 基本的な分割
    text = "こんにちは。元気ですか？はい、元気です。"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 3
    assert chunks[0].text == "こんにちは。"
    assert chunks[1].text == "元気ですか？"
    assert chunks[2].text == "はい、元気です。"

    # 空のテキスト
    assert chunker.chunk("", config) == []

    # 句点がない場合
    text = "こんにちは元気ですか"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 1
    assert chunks[0].text == "こんにちは元気ですか"

def test_character_count_chunker():
    chunker = CharacterCountChunker()
    config = ChunkConfig(strategy=ChunkStrategy.CHARACTER_COUNT, max_chars=5)
    
    # 基本的な分割
    text = "あいうえおかきくけこ"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 2 # "あいうえお", "かきくけこ" は 5文字ずつ
    # 実際には 5, 5 で分割されるはず
    assert chunks[0].text == "あいうえお"
    assert chunks[1].text == "かきくけこ"

    # 境界値
    text = "abcde"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 1
    assert chunks[0].text == "abcde"

def test_hybrid_chunker():
    chunker = HybridChunker()
    
    # ケース 1: すべての文が max_chars 以下
    config = ChunkConfig(strategy=ChunkStrategy.HYBRID, max_chars=50)
    text = "短い文です。短い文です。"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 2
    assert not any(c.is_partial for c in chunks)

    # ケース 2: 文が max_chars を超える場合 (強制分割)
    config = ChunkConfig(strategy=ChunkStrategy.HYBRID, max_chars=10)
    text = "これは非常に長い文章なので、途中で切れるはずです。"
    chunks = chunker.chunk(text, config)
    # "これは非常に長い文章なので、" (13文字) -> 10文字で切る
    assert any(c.is_partial for c in chunks)
    assert chunks[0].char_count <= 10
    
    # ケース 3: 句点がない長い文
    text = "あいうえおかきくけこさしすせそたちつてと"
    chunks = chunker.chunk(text, config)
    assert len(chunks) > 1
    assert any(c.is_partial for c in chunks)

if __name__ == "__main__":
    pytest.main([__file__])
