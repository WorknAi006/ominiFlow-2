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

def get_embedding_provider(tenant_id: str) -> EmbeddingProvider:
    """
    Factory to retrieve the tenant's AI provider.
    Currently always returns MockEmbeddingProvider to prevent live API calls.
    """
    # TODO: Load tenant_ai_configs, decrypt API key safely, and initialize real provider (e.g., OpenAI).
    return MockEmbeddingProvider()
