"""
RAG retrieval interface.
Exposes query(text, k) to retrieve relevant tax law chunks.
"""

import logging
from functools import lru_cache
from typing import Optional

from backend.rag.embeddings import get_vectorstore

logger = logging.getLogger(__name__)


class TaxRAGRetriever:
    """Retrieves relevant Indian tax law chunks from ChromaDB."""

    def __init__(self):
        self._vectorstore = None

    def _get_vs(self):
        if self._vectorstore is None:
            self._vectorstore = get_vectorstore()
        return self._vectorstore

    def query(self, text: str, k: int = 3) -> list[str]:
        """
        Query the tax knowledge base.
        Returns list of relevant text chunks.
        """
        try:
            vs = self._get_vs()
            docs = vs.similarity_search(text, k=k)
            return [doc.page_content for doc in docs]
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return []

    def query_with_scores(self, text: str, k: int = 3) -> list[tuple[str, float]]:
        """Returns list of (chunk_text, relevance_score) tuples."""
        try:
            vs = self._get_vs()
            results = vs.similarity_search_with_score(text, k=k)
            return [(doc.page_content, float(score)) for doc, score in results]
        except Exception as e:
            logger.error(f"RAG scored query failed: {e}")
            return []


@lru_cache(maxsize=1)
def get_retriever() -> TaxRAGRetriever:
    return TaxRAGRetriever()
