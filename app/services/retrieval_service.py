import re
from dataclasses import dataclass
from pathlib import Path

from app.models import Evidence, RunbookInfo
from app.services.embedding_service import TfidfEmbedding


@dataclass(frozen=True)
class Chunk:
    source_id: str
    runbook_id: str
    title: str
    section: str
    text: str


def load_chunks(directory: Path, chunk_size: int = 1000) -> list[Chunk]:
    if chunk_size < 100:
        raise ValueError("chunk_size must be at least 100")
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise ValueError("No Markdown runbooks found")
    chunks: list[Chunk] = []
    for path in paths:
        if not re.fullmatch(r"[a-z0-9-]+", path.stem):
            raise ValueError("Runbook names must use lowercase letters, numbers, and hyphens")
        if path.stat().st_size > 100000:
            raise ValueError("Runbooks must be at most 100 KB each")
        content = path.read_text(encoding="utf-8").strip()
        lines = content.splitlines()
        if not lines or not lines[0].startswith("# "):
            raise ValueError("Each runbook must start with a Markdown title")
        title = lines[0][2:].strip()
        if not title or len(title) > 200:
            raise ValueError("Runbook titles must contain 1 to 200 characters")
        section = "Overview"
        buffer: list[str] = []
        sections: list[tuple[str, str]] = []
        for line in lines[1:]:
            if line.startswith("## "):
                sections.append((section, "\n".join(buffer).strip()))
                section, buffer = line[3:].strip(), []
                if not section or len(section) > 200:
                    raise ValueError("Section headings must contain 1 to 200 characters")
            else:
                buffer.append(line)
        sections.append((section, "\n".join(buffer).strip()))
        ordinal = 0
        for section, body in sections:
            while body:
                boundary = min(len(body), chunk_size)
                if boundary < len(body):
                    whitespace = body.rfind(" ", 0, boundary)
                    if whitespace > chunk_size // 2:
                        boundary = whitespace
                part, body = body[:boundary].strip(), body[boundary:].strip()
                if part:
                    ordinal += 1
                    chunks.append(
                        Chunk(f"{path.stem}#{ordinal:03d}", path.stem, title, section, part)
                    )
        if ordinal == 0:
            raise ValueError("Runbooks must include body text")
        if len(chunks) > 2000:
            raise ValueError("This in-memory demo supports at most 2000 chunks")
    return chunks


class Retriever:
    def __init__(self, chunks: list[Chunk], min_similarity: float = 0.12) -> None:
        self.chunks = tuple(chunks)
        self.min_similarity = min_similarity
        texts = [f"{chunk.title}\n{chunk.section}\n{chunk.text}" for chunk in chunks]
        self.embedding = TfidfEmbedding(texts)
        self.vectors = tuple(self.embedding.embed(text) for text in texts)

    def search(self, query: str, top_k: int = 3) -> list[Evidence]:
        if not 1 <= top_k <= 5:
            raise ValueError("top_k must be between 1 and 5")
        vector = self.embedding.embed(query)
        ranked = sorted(
            (
                (self.embedding.cosine(vector, stored), chunk)
                for chunk, stored in zip(self.chunks, self.vectors, strict=True)
            ),
            key=lambda item: (-item[0], item[1].source_id),
        )
        return [
            Evidence(
                source_id=chunk.source_id,
                runbook_id=chunk.runbook_id,
                title=chunk.title,
                section=chunk.section,
                text=chunk.text,
                score=round(score, 6),
            )
            for score, chunk in ranked[:top_k]
            if score >= self.min_similarity
        ]

    def list_runbooks(self) -> list[RunbookInfo]:
        counts: dict[str, RunbookInfo] = {}
        for chunk in self.chunks:
            if chunk.runbook_id not in counts:
                counts[chunk.runbook_id] = RunbookInfo(
                    runbook_id=chunk.runbook_id,
                    title=chunk.title,
                    chunks=0,
                )
            counts[chunk.runbook_id].chunks += 1
        return list(counts.values())
