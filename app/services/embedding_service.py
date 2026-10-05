import math
import re
from collections import Counter

STOP_WORDS = frozenset(
    "a an and are as at be by for from in is it of on or that the to was with".split()
)


def tokenize(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9]+", text.lower()) if term not in STOP_WORDS]


class TfidfEmbedding:
    """Sparse lexical embeddings: sublinear TF, smoothed IDF, and L2 normalization."""

    def __init__(self, documents: list[str]) -> None:
        frequencies: Counter[str] = Counter()
        for document in documents:
            frequencies.update(set(tokenize(document)))
        if not frequencies:
            raise ValueError("The runbook corpus has no indexable terms")
        self.idf = {
            term: math.log((1 + len(documents)) / (1 + count)) + 1
            for term, count in frequencies.items()
        }

    def embed(self, text: str) -> dict[str, float]:
        counts = Counter(tokenize(text))
        vector = {
            term: (1 + math.log(count)) * self.idf[term]
            for term, count in counts.items()
            if term in self.idf
        }
        magnitude = math.sqrt(sum(value * value for value in vector.values()))
        return {term: value / magnitude for term, value in vector.items()} if magnitude else {}

    @staticmethod
    def cosine(left: dict[str, float], right: dict[str, float]) -> float:
        return min(1.0, max(0.0, sum(weight * right.get(term, 0) for term, weight in left.items())))
