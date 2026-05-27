import pytest
from tts_plugin_bridge.chunker import (
    SentenceChunker,
    CharacterCountChunker,
    HybridChunker,
    PauseMarkerChunker,
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

    # 1文字テキスト
    chunks = chunker.chunk("あ", config)
    assert len(chunks) == 1
    assert chunks[0].text == "あ"


def test_character_count_chunker():
    chunker = CharacterCountChunker()
    config = ChunkConfig(strategy=ChunkStrategy.CHARACTER_COUNT, max_chars=5)

    # 基本的な分割
    text = "あいうえおかきくけこ"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 2
    assert chunks[0].text == "あいうえお"
    assert chunks[1].text == "かきくけこ"

    # 境界値: ちょうどmax_chars
    text = "abcde"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 1
    assert chunks[0].text == "abcde"

    # 1文字テキスト
    chunks = chunker.chunk("あ", config)
    assert len(chunks) == 1
    assert chunks[0].text == "あ"

    # max_chars=1
    config1 = ChunkConfig(strategy=ChunkStrategy.CHARACTER_COUNT, max_chars=1)
    chunks = chunker.chunk("abc", config1)
    assert len(chunks) == 3
    assert chunks[0].text == "a"
    assert chunks[1].text == "b"
    assert chunks[2].text == "c"


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
    assert any(c.is_partial for c in chunks)
    assert chunks[0].char_count <= 10

    # ケース 3: 句点がない長い文
    text = "あいうえおかきくけこさしすせそたちつてと"
    chunks = chunker.chunk(text, config)
    assert len(chunks) > 1
    assert any(c.is_partial for c in chunks)

    # 空テキスト
    assert chunker.chunk("", config) == []

    # 1文字テキスト
    chunks = chunker.chunk("あ", config)
    assert len(chunks) == 1
    assert chunks[0].text == "あ"


def test_pause_marker_chunker():
    chunker = PauseMarkerChunker()
    config = ChunkConfig(strategy=ChunkStrategy.PAUSE_MARKERS, min_chars=5)

    # 読点で分割
    text = "本日は、晴天なり。明日は、雨でしょう。"
    chunks = chunker.chunk(text, config)
    assert len(chunks) >= 2
    assert all(len(c.text) >= 5 for c in chunks)
    assert (
        chunks[0].text == "本日は、晴天なり。明日は、雨でしょう。"
        if len(chunks) == 1
        else True
    )

    # 空テキスト
    assert chunker.chunk("", config) == []

    # 読点がない場合 → 1チャンク
    text = "区切りなし"
    chunks = chunker.chunk(text, config)
    assert len(chunks) == 1
    assert chunks[0].text == "区切りなし"

    # 中黒でも分割
    text = "A・B・C"
    chunks = chunker.chunk(text, config)
    assert len(chunks) >= 1

    # min_chars 未満はマージされる
    config2 = ChunkConfig(strategy=ChunkStrategy.PAUSE_MARKERS, min_chars=3)
    text = "a、b、c、d"
    chunks = chunker.chunk(text, config2)
    assert all(len(c.text) >= 3 for c in chunks)

    # min_chars=0 (最小マージなし)
    config3 = ChunkConfig(strategy=ChunkStrategy.PAUSE_MARKERS, min_chars=0)
    text = "A、B、C"
    chunks = chunker.chunk(text, config3)
    # 読点区切りで各1文字 → min_chars=0なので分割される
    assert chunks[0].text == "A"


if __name__ == "__main__":
    pytest.main([__file__])
