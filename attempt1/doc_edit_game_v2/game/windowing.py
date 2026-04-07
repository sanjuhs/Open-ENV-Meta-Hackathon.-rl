"""Document windowing system for handling large documents via chunked navigation."""

from typing import List, Optional
import re


class DocumentWindow:
    """Manages chunked access to a large document."""

    def __init__(self, document: str, chunk_size: int = 50):
        self.lines = document.split("\n")
        self.chunk_size = chunk_size
        self.current_chunk = 0

    @property
    def total_chunks(self) -> int:
        return max(1, (len(self.lines) + self.chunk_size - 1) // self.chunk_size)

    @property
    def full_document(self) -> str:
        return "\n".join(self.lines)

    @full_document.setter
    def full_document(self, value: str):
        self.lines = value.split("\n")

    def get_chunk(self, chunk_index: Optional[int] = None) -> str:
        idx = chunk_index if chunk_index is not None else self.current_chunk
        idx = max(0, min(idx, self.total_chunks - 1))
        start = idx * self.chunk_size
        end = min(start + self.chunk_size, len(self.lines))
        return "\n".join(self.lines[start:end])

    def get_overview(self) -> str:
        """High-level overview: list headings with their chunk indices."""
        parts = []
        for i, line in enumerate(self.lines):
            if line.startswith("<heading"):
                chunk_idx = i // self.chunk_size
                text = re.sub(r'<[^>]+>', '', line).strip()
                parts.append(f"[chunk {chunk_idx}, line {i}] {text}")
        if not parts:
            return f"Document has {len(self.lines)} lines across {self.total_chunks} chunks."
        return "\n".join(parts)

    def get_chunk_summary(self, chunk_index: int) -> str:
        """Short summary of a chunk: first heading or first line."""
        chunk = self.get_chunk(chunk_index)
        lines = chunk.split("\n")
        for line in lines:
            if line.startswith("<heading"):
                return re.sub(r'<[^>]+>', '', line).strip()
        if lines:
            text = re.sub(r'<[^>]+>', '', lines[0]).strip()
            return text[:80] + "..." if len(text) > 80 else text
        return f"Chunk {chunk_index} (empty)"

    def scroll_to(self, chunk_index: int) -> str:
        self.current_chunk = max(0, min(chunk_index, self.total_chunks - 1))
        return self.get_chunk()

    def search_forward(self, query: str) -> Optional[int]:
        """Find next chunk containing query after current position."""
        start_line = (self.current_chunk + 1) * self.chunk_size
        for i in range(start_line, len(self.lines)):
            if query in self.lines[i]:
                return i // self.chunk_size
        return None

    def search_backward(self, query: str) -> Optional[int]:
        """Find previous chunk containing query before current position."""
        end_line = self.current_chunk * self.chunk_size
        for i in range(end_line - 1, -1, -1):
            if query in self.lines[i]:
                return i // self.chunk_size
        return None

    def is_small_document(self) -> bool:
        return self.total_chunks <= 2
