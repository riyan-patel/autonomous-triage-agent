from abc import ABC, abstractmethod

from .config import EMBEDDING_DIM


class Embedder(ABC):
    dimension: int = EMBEDDING_DIM

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return a dense vector representation of `text`."""


class SentenceTransformerEmbedder(Embedder):
    """Local, no-API-key embedder - the model downloads once (~90MB) and
    runs on CPU, so retrieval works without depending on the swappable LLM
    provider or an embeddings API being configured.
    """

    def __init__(self, model_name: str) -> None:
        # Imported lazily so importing this module doesn't require
        # sentence-transformers to be installed unless it's actually used
        # (e.g. tests inject a fake embedder instead).
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()
