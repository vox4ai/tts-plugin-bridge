import re
from typing import List, Protocol
from .protocol import ChunkResult, ChunkConfig


class TextChunker(Protocol):
    def chunk(self, text: str, config: ChunkConfig) -> List[ChunkResult]: ...


class SentenceChunker:
    """句点で分割"""

    def chunk(self, text: str, config: ChunkConfig) -> List[ChunkResult]:
        if not text:
            return []

        # 句点(。！？)を保持して分割するための正規表現
        pattern = r"([。！？])"
        parts = re.split(pattern, text)

        combined_parts = []
        for i in range(0, len(parts) - 1, 2):
            combined_parts.append(parts[i] + parts[i + 1])

        if len(parts) % 2 != 0 and parts[-1]:
            combined_parts.append(parts[-1])

        results = []
        for idx, part in enumerate(combined_parts):
            if part:
                results.append(ChunkResult(text=part, index=idx, char_count=len(part)))
        return results


class CharacterCountChunker:
    """文字数で分割"""

    def chunk(self, text: str, config: ChunkConfig) -> List[ChunkResult]:
        if not text:
            return []

        max_chars = config.max_chars
        results = []

        for i in range(0, len(text), max_chars):
            chunk_text = text[i : i + max_chars]
            results.append(
                ChunkResult(
                    text=chunk_text, index=len(results), char_count=len(chunk_text)
                )
            )
        return results


class HybridChunker:
    """原則sentence分割、max_chars超えりでchar分割"""

    def __init__(self):
        self.sentence_chunker = SentenceChunker()
        self.char_chunker = CharacterCountChunker()

    def chunk(self, text: str, config: ChunkConfig) -> List[ChunkResult]:
        if not text:
            return []

        sentence_chunks = self.sentence_chunker.chunk(text, config)

        final_results = []
        current_index = 0

        for s_chunk in sentence_chunks:
            if len(s_chunk.text) <= config.max_chars:
                final_results.append(
                    ChunkResult(
                        text=s_chunk.text,
                        index=current_index,
                        char_count=s_chunk.char_count,
                        is_partial=False,
                    )
                )
                current_index += 1
            else:
                sub_chunks = self.char_chunker.chunk(s_chunk.text, config)

                for i, sub in enumerate(sub_chunks):
                    is_last = i == len(sub_chunks) - 1
                    final_results.append(
                        ChunkResult(
                            text=sub.text,
                            index=current_index,
                            char_count=sub.char_count,
                            is_partial=not is_last,
                            original_sentence=s_chunk.text,
                        )
                    )
                    current_index += 1

        return final_results


class PauseMarkerChunker:
    def chunk(self, text: str, config: ChunkConfig) -> List[ChunkResult]:
        if not text:
            return []

        _split_re = re.compile(r"[、，・,; 　]+")
        parts = _split_re.split(text)
        parts = [p.strip() for p in parts if p.strip()]
        if not parts:
            return [ChunkResult(text=text, index=0, char_count=len(text))]

        merged: list[str] = []
        for p in parts:
            if merged and len(merged[-1]) < config.min_chars:
                merged[-1] += p
            else:
                merged.append(p)

        if merged and len(merged) > 1 and len(merged[-1]) < config.min_chars:
            tail = merged.pop()
            merged[-1] += tail

        results = []
        for idx, chunk in enumerate(merged):
            results.append(
                ChunkResult(
                    text=chunk,
                    index=idx,
                    char_count=len(chunk),
                    is_partial=(idx < len(merged) - 1),
                )
            )
        return results
