"""
Ingest Indian tax law knowledge base into ChromaDB.
Called once on startup if collection is empty.
"""

import os
import logging
from pathlib import Path

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import TextLoader
    LANGCHAIN_AVAILABLE = True
except ImportError:
    RecursiveCharacterTextSplitter = None
    TextLoader = None
    LANGCHAIN_AVAILABLE = False

from backend.rag.embeddings import get_vectorstore, get_chroma_client, COLLECTION_NAME

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "data" / "tax_knowledge_base.txt"


def ingest_knowledge_base(force: bool = False) -> int:
    """
    Ingest tax knowledge base into ChromaDB.
    Skips if already ingested (unless force=True).
    Returns number of chunks ingested.
    """
    if not LANGCHAIN_AVAILABLE:
        logger.warning("LangChain packages not available — RAG ingestion skipped")
        return 0
    
    client = get_chroma_client()

    # Check if already ingested
    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        if count > 0 and not force:
            logger.info(f"Knowledge base already ingested ({count} chunks). Skipping.")
            return count
    except Exception:
        pass  # Collection doesn't exist yet

    if not KNOWLEDGE_BASE_PATH.exists():
        logger.error(f"Knowledge base file not found: {KNOWLEDGE_BASE_PATH}")
        return 0

    logger.info(f"Loading knowledge base from: {KNOWLEDGE_BASE_PATH}")

    loader = TextLoader(str(KNOWLEDGE_BASE_PATH), encoding="utf-8")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n\n", "\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(documents)

    logger.info(f"Splitting into {len(chunks)} chunks")

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)

    logger.info(f"Successfully ingested {len(chunks)} chunks into ChromaDB")
    return len(chunks)
