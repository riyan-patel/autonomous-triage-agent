import hashlib

from retrieval.config import EMBEDDING_DIM
from retrieval.embeddings import Embedder


class FakeEmbedder(Embedder):
    """Deterministic, offline stand-in for SentenceTransformerEmbedder.

    Hashes overlapping word-shingles into vector components so that texts
    sharing words end up with non-trivial cosine similarity (unlike a pure
    random-per-text vector, which would make "near duplicate" tests
    meaningless) - without downloading any model or hitting the network.
    """

    def __init__(self, dimension: int = EMBEDDING_DIM) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        words = text.lower().split()
        for word in words:
            digest = hashlib.sha256(word.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = sum(v * v for v in vector) ** 0.5
        if norm == 0:
            return vector
        return [v / norm for v in vector]
