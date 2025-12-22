"""
Retrieval Pipeline for Offline Private LLM-RAG System
Implements semantic search with optional re-ranking and filtering
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..vectordb.vector_store import VectorStore, MetadataDatabase
from ..embedding.embedding_generator import OfflineEmbeddingGenerator
from ..config import ClassificationLevel


logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Represents a retrieval result"""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    rank: int


class SemanticRetriever:
    """
    Semantic retrieval using vector similarity
    """
    
    def __init__(self,
                 vector_store: VectorStore,
                 embedding_generator: OfflineEmbeddingGenerator,
                 metadata_db: Optional[MetadataDatabase] = None):
        """
        Initialize retriever
        
        Args:
            vector_store: Vector store for similarity search
            embedding_generator: Embedding generator for queries
            metadata_db: Optional metadata database for full content
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.metadata_db = metadata_db
    
    def retrieve(self,
                query: str,
                top_k: int = 5,
                similarity_threshold: float = 0.0,
                classification_filter: Optional[ClassificationLevel] = None,
                metadata_filters: Optional[Dict[str, Any]] = None) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for a query
        
        Args:
            query: User query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            classification_filter: Maximum classification level allowed
            metadata_filters: Additional metadata filters
        
        Returns:
            List of RetrievalResult objects
        """
        logger.info(f"Retrieving for query: {query[:100]}...")
        
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Search vector store
        raw_results = self.vector_store.search(
            query_embedding,
            top_k=top_k,
            classification_filter=classification_filter,
            metadata_filters=metadata_filters
        )
        
        # Filter by similarity threshold
        filtered_results = [
            r for r in raw_results
            if r["score"] >= similarity_threshold
        ]
        
        # Build retrieval results
        results = []
        for rank, result in enumerate(filtered_results):
            chunk_id = result["chunk_id"]
            
            # Get full content from metadata DB if available
            content = None
            if self.metadata_db:
                chunk_data = self.metadata_db.get_chunk(chunk_id)
                if chunk_data:
                    content = chunk_data["content"]
            
            # Fall back to metadata (may be truncated)
            if content is None:
                content = result["metadata"].get("content", "")
            
            results.append(RetrievalResult(
                chunk_id=chunk_id,
                content=content,
                score=result["score"],
                metadata=result["metadata"],
                rank=rank
            ))
        
        logger.info(f"Retrieved {len(results)} results (threshold: {similarity_threshold})")
        return results


class HybridRetriever(SemanticRetriever):
    """
    Hybrid retrieval combining semantic search and keyword matching
    """
    
    def __init__(self,
                 vector_store: VectorStore,
                 embedding_generator: OfflineEmbeddingGenerator,
                 metadata_db: MetadataDatabase,
                 semantic_weight: float = 0.7):
        """
        Initialize hybrid retriever
        
        Args:
            vector_store: Vector store
            embedding_generator: Embedding generator
            metadata_db: Metadata database (required for text search)
            semantic_weight: Weight for semantic score (0-1)
        """
        super().__init__(vector_store, embedding_generator, metadata_db)
        self.semantic_weight = semantic_weight
        self.keyword_weight = 1.0 - semantic_weight
    
    def retrieve(self,
                query: str,
                top_k: int = 5,
                similarity_threshold: float = 0.0,
                classification_filter: Optional[ClassificationLevel] = None,
                metadata_filters: Optional[Dict[str, Any]] = None) -> List[RetrievalResult]:
        """
        Retrieve using both semantic and keyword search
        """
        # Semantic search
        semantic_results = super().retrieve(
            query,
            top_k=top_k * 2,  # Get more for merging
            similarity_threshold=0.0,  # No threshold yet
            classification_filter=classification_filter,
            metadata_filters=metadata_filters
        )
        
        # Keyword search
        keyword_results = []
        if self.metadata_db:
            keyword_chunks = self.metadata_db.search_text(query, limit=top_k * 2)
            for rank, chunk_data in enumerate(keyword_chunks):
                # Apply classification filter
                if classification_filter:
                    chunk_class = ClassificationLevel[chunk_data["classification"]]
                    if chunk_class > classification_filter:
                        continue
                
                keyword_results.append({
                    "chunk_id": chunk_data["chunk_id"],
                    "content": chunk_data["content"],
                    "rank": rank
                })
        
        # Merge results using reciprocal rank fusion
        merged = self._merge_results(semantic_results, keyword_results, top_k)
        
        # Apply similarity threshold
        filtered = [r for r in merged if r.score >= similarity_threshold]
        
        logger.info(f"Hybrid retrieval: {len(filtered)} results after merging")
        return filtered[:top_k]
    
    def _merge_results(self,
                      semantic_results: List[RetrievalResult],
                      keyword_results: List[Dict[str, Any]],
                      top_k: int) -> List[RetrievalResult]:
        """
        Merge semantic and keyword results using reciprocal rank fusion
        """
        # Build score map
        scores = {}
        contents = {}
        metadatas = {}
        
        # Add semantic scores
        for result in semantic_results:
            chunk_id = result.chunk_id
            # Reciprocal rank fusion: 1 / (k + rank)
            rrf_score = 1.0 / (60 + result.rank)
            scores[chunk_id] = rrf_score * self.semantic_weight
            contents[chunk_id] = result.content
            metadatas[chunk_id] = result.metadata
        
        # Add keyword scores
        for result in keyword_results:
            chunk_id = result["chunk_id"]
            rrf_score = 1.0 / (60 + result["rank"])
            if chunk_id in scores:
                scores[chunk_id] += rrf_score * self.keyword_weight
            else:
                scores[chunk_id] = rrf_score * self.keyword_weight
                contents[chunk_id] = result["content"]
                metadatas[chunk_id] = {"content": result["content"]}
        
        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # Build results
        merged = []
        for rank, chunk_id in enumerate(sorted_ids[:top_k]):
            merged.append(RetrievalResult(
                chunk_id=chunk_id,
                content=contents[chunk_id],
                score=scores[chunk_id],
                metadata=metadatas[chunk_id],
                rank=rank
            ))
        
        return merged


class ReRanker:
    """
    Re-rank retrieved results using cross-encoder (optional enhancement)
    For now, implements simple heuristic re-ranking
    """
    
    def rerank(self,
              query: str,
              results: List[RetrievalResult],
              top_k: Optional[int] = None) -> List[RetrievalResult]:
        """
        Re-rank results
        
        Args:
            query: User query
            results: Initial retrieval results
            top_k: Number of results to return after re-ranking
        
        Returns:
            Re-ranked results
        """
        if not results:
            return results
        
        # Simple heuristic re-ranking based on:
        # 1. Query term coverage
        # 2. Document length (prefer medium length)
        # 3. Original similarity score
        
        query_terms = set(query.lower().split())
        
        scored_results = []
        for result in results:
            content_lower = result.content.lower()
            
            # Query term coverage (0-1)
            matching_terms = sum(1 for term in query_terms if term in content_lower)
            coverage_score = matching_terms / len(query_terms) if query_terms else 0
            
            # Length penalty (prefer 200-1000 chars)
            length = len(result.content)
            if 200 <= length <= 1000:
                length_score = 1.0
            elif length < 200:
                length_score = length / 200
            else:
                length_score = max(0.5, 1000 / length)
            
            # Combined score
            rerank_score = (
                0.5 * result.score +      # Original similarity
                0.3 * coverage_score +    # Query coverage
                0.2 * length_score        # Length preference
            )
            
            scored_results.append((rerank_score, result))
        
        # Sort by re-rank score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Update ranks
        reranked = []
        for rank, (score, result) in enumerate(scored_results):
            result.rank = rank
            result.score = score  # Update with re-rank score
            reranked.append(result)
        
        if top_k:
            reranked = reranked[:top_k]
        
        logger.info(f"Re-ranked {len(reranked)} results")
        return reranked


def format_context(results: List[RetrievalResult], include_metadata: bool = True) -> str:
    """
    Format retrieval results into context for LLM
    
    Args:
        results: Retrieval results
        include_metadata: Include source metadata
    
    Returns:
        Formatted context string
    """
    if not results:
        return "No relevant documents found."
    
    context_parts = []
    
    for result in results:
        # Extract source information
        source_file = result.metadata.get("source_file", "Unknown")
        classification = result.metadata.get("classification", "UNCLASSIFIED")
        doc_type = result.metadata.get("document_type", "document")
        
        # Format chunk
        chunk_text = f"[Document {result.rank + 1}]"
        
        if include_metadata:
            chunk_text += f"\n[Source: {source_file}]"
            chunk_text += f"\n[Classification: {classification}]"
            chunk_text += f"\n[Relevance: {result.score:.3f}]"
        
        chunk_text += f"\n\n{result.content}\n"
        
        context_parts.append(chunk_text)
    
    return "\n".join(context_parts)
