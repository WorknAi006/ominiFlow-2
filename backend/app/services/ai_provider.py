import abc
from typing import List

class EmbeddingProvider(abc.ABC):
    """Abstract interface for generating embeddings safely without exposing credentials."""
    
    @abc.abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abc.abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass
        
    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        pass
        
    @property
    @abc.abstractmethod
    def model_version(self) -> str:
        pass
        
    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        pass

class MockEmbeddingProvider(EmbeddingProvider):
    """Fallback mock provider for automated tests and when credentials are missing."""
    def embed_text(self, text: str) -> List[float]:
        # Return a dummy vector of 1536 dimensions
        return [0.01] * 1536

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

    @property
    def model_name(self) -> str:
        return "mock-embedding-model"
        
    @property
    def model_version(self) -> str:
        return "1.0"

    @property
    def dimension(self) -> int:
        return 1536

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Real embeddings via OpenAI. text-embedding-3-small is 1536-dimensional,
    matching the mock and the stored chunk vector size."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._api_key = api_key
        self._model = model

    def _client(self):
        from openai import OpenAI
        return OpenAI(api_key=self._api_key)

    def embed_text(self, text: str) -> List[float]:
        resp = self._client().embeddings.create(model=self._model, input=[text or " "])
        return list(resp.data[0].embedding)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        resp = self._client().embeddings.create(model=self._model, input=[t or " " for t in texts])
        return [list(item.embedding) for item in resp.data]

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def model_version(self) -> str:
        return "1"

    @property
    def dimension(self) -> int:
        return 1536


def get_embedding_provider(tenant_id: str) -> EmbeddingProvider:
    """
    Return the embedding provider. Uses the platform OpenAI key when
    configured (OPENAI_API_KEY); otherwise falls back to the mock provider so
    tests and key-less environments keep working. Switching from mock to real
    embeddings requires re-embedding existing knowledge-base documents.
    """
    from app.core.config import settings

    key = (settings.openai_api_key or "").strip()
    if key:
        return OpenAIEmbeddingProvider(key, model=getattr(settings, "openai_embedding_model", "text-embedding-3-small"))
    return MockEmbeddingProvider()
