import math

import pytest

from app.services.embedding_service import TfidfEmbedding
from app.services.retrieval_service import Chunk, Retriever, load_chunks


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("database pool exhausted connection acquisition timeout", "database-pool"),
        ("container OOMKilled memory pressure exit 137", "memory-pressure"),
        ("queue backlog consumer lag poison messages", "queue-backlog"),
        ("upstream gateway HTTP 504 dependency timeout", "upstream-timeout"),
        ("AEM Dispatcher stale cache activation replication", "aem-dispatcher"),
        ("authentication token issuer secret rotation 401", "authentication-failure"),
    ],
)
def test_known_symptoms_rank_relevant_runbook_first(retriever, query, expected):
    results = retriever.search(query)
    assert results[0].runbook_id == expected
    assert all(0 < result.score <= 1 for result in results)
    assert [result.score for result in results] == sorted(
        [result.score for result in results],
        reverse=True,
    )


def test_unknown_terms_and_stop_words_return_no_evidence(retriever):
    assert retriever.search("quux zyzzyva") == []
    assert retriever.search("the and of") == []


def test_embeddings_are_normalized_and_cosine_behaves():
    embedding = TfidfEmbedding(["database pool", "container memory"])
    vector = embedding.embed("database pool pool")
    assert math.sqrt(sum(weight**2 for weight in vector.values())) == pytest.approx(1)
    assert embedding.cosine(vector, vector) == pytest.approx(1)
    assert embedding.cosine(vector, embedding.embed("memory")) == 0
    assert embedding.embed("unknown") == {}


def test_ties_have_stable_source_order():
    chunks = [
        Chunk(f"demo#{ordinal:03d}", "demo", "Same", "Same", "database pool") for ordinal in (2, 1)
    ]
    assert [hit.source_id for hit in Retriever(chunks).search("database")] == [
        "demo#001",
        "demo#002",
    ]


def test_chunking_preserves_long_text_and_unique_citations(tmp_path):
    body = "memory pressure " * 200
    (tmp_path / "long.md").write_text(f"# Long runbook\n\n## Details\n{body}", encoding="utf-8")
    chunks = load_chunks(tmp_path, chunk_size=200)
    assert len(chunks) > 1
    assert len({chunk.source_id for chunk in chunks}) == len(chunks)
    assert all(len(chunk.text) <= 200 for chunk in chunks)
    assert " ".join(chunk.text for chunk in chunks).split() == body.split()


@pytest.mark.parametrize("content", ["", "No title", "# Empty", "# \nbody", "# Title\n## \nbody"])
def test_malformed_runbooks_fail_startup(tmp_path, content):
    (tmp_path / "bad.md").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_chunks(tmp_path)


def test_empty_directory_is_not_silently_accepted(tmp_path):
    with pytest.raises(ValueError, match="No Markdown"):
        load_chunks(tmp_path)


def test_invalid_filename_rejected(tmp_path):
    (tmp_path / "Bad Name.md").write_text("# Title\ncontent", encoding="utf-8")
    with pytest.raises(ValueError, match="Runbook names"):
        load_chunks(tmp_path)


def test_oversized_runbook_rejected(tmp_path):
    (tmp_path / "large.md").write_text("# Large\n" + "x" * 100001, encoding="utf-8")
    with pytest.raises(ValueError, match="100 KB"):
        load_chunks(tmp_path)


def test_empty_embedding_corpus_rejected():
    with pytest.raises(ValueError, match="no indexable terms"):
        TfidfEmbedding(["the and of"])


def test_top_k_bounds(retriever):
    with pytest.raises(ValueError):
        retriever.search("database", 0)
    assert len(retriever.search("database", 1)) == 1
