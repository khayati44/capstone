"""
Enhanced RAG Pipeline with FAISS Vector Database
Implements proper document embedding and retrieval for tax rules
"""

import os
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try importing RAG dependencies with proper fallbacks
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG dependencies not available: {e}")
    RAG_AVAILABLE = False


@dataclass
class RetrievedContext:
    """Retrieved context from RAG pipeline"""
    content: str
    metadata: dict
    score: float


class TaxKnowledgeRAG:
    """
    RAG system for tax deduction rules using FAISS vector database.
    Demonstrates proper RAG implementation for capstone requirements.
    """
    
    def __init__(self, knowledge_base_path: str = "backend/data/tax_knowledge_base.txt"):
        self.knowledge_base_path = knowledge_base_path
        self.vectorstore = None
        self.embeddings = None
        self.is_initialized = False
        
        if RAG_AVAILABLE:
            self._initialize_rag()
    
    def _initialize_rag(self):
        """Initialize embeddings and vector store"""
        try:
            # Use lightweight sentence-transformers model
            logger.info("Initializing RAG with HuggingFace embeddings...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Check if vectorstore exists
            vectorstore_path = "backend/data/faiss_index"
            if os.path.exists(vectorstore_path):
                logger.info("Loading existing FAISS index...")
                self.vectorstore = FAISS.load_local(
                    vectorstore_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                logger.info("Creating new FAISS index from knowledge base...")
                self._create_vectorstore()
            
            self.is_initialized = True
            logger.info("RAG pipeline initialized successfully!")
            
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            self.is_initialized = False
    
    def _create_vectorstore(self):
        """Create vector store from knowledge base documents"""
        # Load tax knowledge base
        if not os.path.exists(self.knowledge_base_path):
            logger.warning(f"Knowledge base not found at {self.knowledge_base_path}")
            return
        
        with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " "]
        )
        
        chunks = text_splitter.split_text(content)
        documents = [
            Document(page_content=chunk, metadata={"source": "tax_rules", "chunk_id": i})
            for i, chunk in enumerate(chunks)
        ]
        
        logger.info(f"Creating vector store with {len(documents)} chunks...")
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        
        # Save for future use
        vectorstore_path = "backend/data/faiss_index"
        os.makedirs(os.path.dirname(vectorstore_path), exist_ok=True)
        self.vectorstore.save_local(vectorstore_path)
        logger.info(f"Vector store saved to {vectorstore_path}")
    
    def retrieve_context(self, query: str, k: int = 3) -> List[RetrievedContext]:
        """
        Retrieve relevant context for a query using semantic search.
        
        Args:
            query: Search query
            k: Number of top results to return
            
        Returns:
            List of retrieved contexts with scores
        """
        if not self.is_initialized or not self.vectorstore:
            logger.warning("RAG not initialized, returning empty context")
            return []
        
        try:
            # Perform similarity search with scores
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            retrieved = [
                RetrievedContext(
                    content=doc.page_content,
                    metadata=doc.metadata,
                    score=float(score)
                )
                for doc, score in results
            ]
            
            logger.info(f"Retrieved {len(retrieved)} contexts for query: '{query[:50]}...'")
            return retrieved
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []
    
    def augment_prompt(self, query: str, base_prompt: str) -> str:
        """
        Augment a prompt with retrieved context (RAG pattern).
        
        Args:
            query: User query to find relevant context
            base_prompt: Base prompt to augment
            
        Returns:
            Augmented prompt with retrieved context
        """
        contexts = self.retrieve_context(query, k=3)
        
        if not contexts:
            return base_prompt
        
        # Build context section
        context_text = "\n\n".join([
            f"[Context {i+1} - Score: {ctx.score:.3f}]\n{ctx.content}"
            for i, ctx in enumerate(contexts)
        ])
        
        # Augment prompt
        augmented = f"""You are a tax deduction expert. Use the following retrieved context to answer accurately.

RETRIEVED CONTEXT:
{context_text}

USER QUERY: {query}

INSTRUCTIONS: {base_prompt}

Provide a detailed answer based on the context above. If the context doesn't contain relevant information, acknowledge that and provide general guidance.
"""
        return augmented


# Global instance
_rag_instance: Optional[TaxKnowledgeRAG] = None


def get_rag_system() -> TaxKnowledgeRAG:
    """Get or create RAG system singleton"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = TaxKnowledgeRAG()
    return _rag_instance


def query_tax_knowledge(question: str, k: int = 3) -> List[RetrievedContext]:
    """
    Convenience function to query tax knowledge base.
    
    Example:
        contexts = query_tax_knowledge("What is Section 80C limit?")
        for ctx in contexts:
            print(f"Score: {ctx.score}, Content: {ctx.content}")
    """
    rag = get_rag_system()
    return rag.retrieve_context(question, k=k)
