from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

_embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key, model="text-embedding-ada-002")


def create_embedding(text: str) -> list[float]:
    """Create an embedding vector for a single text string."""
    return _embeddings.embed_query(text)


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """Create embedding vectors for a batch of texts."""
    return _embeddings.embed_documents(texts)
