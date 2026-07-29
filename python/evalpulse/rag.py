from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]+")
HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


@dataclass(frozen=True)
class DocumentChunk:
    citation_id: str
    path: str
    heading: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class KnowledgeRetriever:
    """A tiny in-memory BM25-style retriever for the curated Markdown runbooks."""

    def __init__(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            raise ValueError("The RAG knowledge base contains no document chunks")
        self.chunks = chunks
        self._tokens = [_tokens(chunk.heading + " " + chunk.text) for chunk in chunks]
        self._average_length = sum(map(len, self._tokens)) / len(self._tokens)
        self._document_frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(set(tokens))

    @classmethod
    def from_directory(cls, directory: str | Path) -> KnowledgeRetriever:
        root = Path(directory)
        chunks: list[DocumentChunk] = []
        for path in sorted(root.glob("*.md")):
            chunks.extend(_markdown_chunks(path, root))
        return cls(chunks)

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        query_terms = set(_tokens(query))
        scored: list[RetrievedChunk] = []
        for chunk, tokens in zip(self.chunks, self._tokens, strict=True):
            term_counts = Counter(tokens)
            score = sum(self._bm25(term, term_counts, len(tokens)) for term in query_terms)
            if score > 0:
                scored.append(RetrievedChunk(chunk=chunk, score=round(score, 6)))
        scored.sort(key=lambda item: (-item.score, item.chunk.citation_id))
        return scored[: max(1, top_k)]

    def _bm25(self, term: str, counts: Counter[str], length: int) -> float:
        frequency = counts[term]
        if not frequency:
            return 0.0
        total = len(self.chunks)
        document_frequency = self._document_frequency[term]
        inverse_frequency = math.log(
            1 + (total - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        k1, b = 1.2, 0.75
        denominator = frequency + k1 * (1 - b + b * length / max(self._average_length, 1))
        return inverse_frequency * frequency * (k1 + 1) / denominator


def _markdown_chunks(path: Path, root: Path) -> list[DocumentChunk]:
    relative = path.relative_to(root.parent.parent).as_posix()
    sections: list[tuple[str, list[str]]] = []
    heading = path.stem.replace("-", " ").title()
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            if any(item.strip() for item in lines):
                sections.append((heading, lines))
            heading = match.group(2).strip()
            lines = []
        else:
            lines.append(line)
    if any(item.strip() for item in lines):
        sections.append((heading, lines))
    chunks: list[DocumentChunk] = []
    for section_heading, section_lines in sections:
        text = "\n".join(section_lines).strip()
        if not text:
            continue
        anchor = re.sub(r"[^a-z0-9]+", "-", section_heading.casefold()).strip("-")
        citation_id = f"{path.stem}#{anchor}"
        chunks.append(
            DocumentChunk(
                citation_id=citation_id,
                path=f"{relative}#{anchor}",
                heading=section_heading,
                text=text,
            )
        )
    return chunks


def _tokens(value: str) -> list[str]:
    return TOKEN_PATTERN.findall(value.casefold())
