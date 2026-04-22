"""
Resilient embeddings and vectorstore loader for RAG.

Tries to use langchain_community + Chroma if available. Falls back to
sentence-transformers and a MinimalVectorStore when LangChain community
packages are not importable or incompatible (prevents app startup failures).
"""

import logging
from functools import lru_cache

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "tax_knowledge_base"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# Try to import LangChain community Chroma/HuggingFace wrappers; fall back to
# using sentence-transformers directly and a minimal in-memory vectorstore stub
# if the community packages aren't available or incompatible.
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from langchain_community.vectorstores import Chroma
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _USE_LANGCHAIN_COMMUNITY = True
    except Exception:
        # try langchain_huggingface package
        try:
            from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
            _USE_LANGCHAIN_COMMUNITY = True
        except Exception:
            HuggingFaceEmbeddings = None  # type: ignore
            _USE_LANGCHAIN_COMMUNITY = False
except Exception:
    chromadb = None
    Chroma = None
    HuggingFaceEmbeddings = None
    _USE_LANGCHAIN_COMMUNITY = False


@lru_cache(maxsize=1)
def get_embedding_function():
    """Return an embedding function or object compatible with LangChain-style
    embedding API. Prefer HuggingFaceEmbeddings if available, otherwise use
    sentence-transformers model and return a simple callable.
    """
    if HuggingFaceEmbeddings is not None:
        logger.info(f"Loading HuggingFaceEmbeddings: {EMBEDDING_MODEL}")
        try:
            return HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as e:
            logger.warning(f"HuggingFaceEmbeddings import failed: {e}")

    # Fallback: use sentence-transformers directly
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)

        def embed_texts(texts):
            return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

        logger.info("Using sentence-transformers SentenceTransformer as embedding function")
        return embed_texts
    except Exception as e:
        logger.error(f"No embedding backend available: {e}")
        return None


def get_chroma_client():
    if chromadb is None:
        raise RuntimeError("chromadb not available")
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


class MinimalVectorStore:
    """A minimal fallback vectorstore with no persistence.

    Methods implemented: `similarity_search`, `similarity_search_with_score`.
    This is a best-effort fallback so the app can run without full LangChain
    integration. It returns empty results and logs warnings.
    """

    def __init__(self):
        self._docs = []

    def similarity_search(self, query, k=3):
        logger.warning("MinimalVectorStore: similarity_search called — returning empty list")
        return []

    def similarity_search_with_score(self, query, k=3):
        logger.warning("MinimalVectorStore: similarity_search_with_score called — returning empty list")
        return []


@lru_cache(maxsize=1)
def get_vectorstore():
    """Return a vectorstore object compatible with the retriever usage.

    Prefer a LangChain Chroma wrapper if available; otherwise return a
    `MinimalVectorStore` to keep the application running.
    """
    embeddings = get_embedding_function()
    if _USE_LANGCHAIN_COMMUNITY and Chroma is not None and embeddings is not None:
        logger.info("Using langchain_community.Chroma vectorstore")
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )

    logger.warning("Falling back to MinimalVectorStore — full RAG disabled")
    return MinimalVectorStore()
