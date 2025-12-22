"""
RAG Orchestration Pipeline
Combines retrieval and generation with security controls
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from ..retrieval.retriever import SemanticRetriever, format_context, RetrievalResult
from ..llm.inference import OfflineLLM, PromptTemplate, SafetyFilter
from ..config import ClassificationLevel


logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Represents a RAG system response"""
    query: str
    answer: str
    sources: List[RetrievalResult]
    classification: ClassificationLevel
    timestamp: str
    metadata: Dict[str, Any]
    is_valid: bool = True


class RAGPipeline:
    """
    End-to-end RAG pipeline
    Orchestrates retrieval and generation
    """
    
    def __init__(self,
                 retriever: SemanticRetriever,
                 llm: OfflineLLM,
                 default_classification: ClassificationLevel = ClassificationLevel.UNCLASSIFIED,
                 enable_safety_filter: bool = True):
        """
        Initialize RAG pipeline
        
        Args:
            retriever: Retriever instance
            llm: LLM instance
            default_classification: Default classification level
            enable_safety_filter: Enable response validation
        """
        self.retriever = retriever
        self.llm = llm
        self.default_classification = default_classification
        self.enable_safety_filter = enable_safety_filter
        
        logger.info("RAG Pipeline initialized")
    
    def query(self,
             query: str,
             top_k: int = 5,
             similarity_threshold: float = 0.7,
             user_classification: Optional[ClassificationLevel] = None,
             temperature: Optional[float] = None,
             metadata_filters: Optional[Dict[str, Any]] = None) -> RAGResponse:
        """
        Process a query through the RAG pipeline
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity for retrieval
            user_classification: User's clearance level
            temperature: LLM temperature override
            metadata_filters: Additional filters
        
        Returns:
            RAGResponse object
        """
        logger.info(f"Processing query: {query[:100]}...")
        
        # Validate query
        if not query or len(query.strip()) < 3:
            return self._create_error_response(
                query,
                "Query too short. Please provide a more detailed question."
            )
        
        # Retrieve relevant documents
        try:
            retrieval_results = self.retriever.retrieve(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                classification_filter=user_classification,
                metadata_filters=metadata_filters
            )
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return self._create_error_response(query, "Retrieval error occurred")
        
        # Check if any documents retrieved
        if not retrieval_results:
            return RAGResponse(
                query=query,
                answer="Insufficient information in provided documents. No relevant documents found for your query.",
                sources=[],
                classification=self.default_classification,
                timestamp=datetime.utcnow().isoformat(),
                metadata={"retrieved_count": 0}
            )
        
        # Determine response classification (highest among retrieved docs)
        response_classification = self._determine_classification(retrieval_results)
        
        # Check user clearance
        if user_classification and response_classification > user_classification:
            return self._create_access_denied_response(
                query,
                user_classification,
                response_classification
            )
        
        # Format context
        context = format_context(retrieval_results, include_metadata=True)
        
        # Generate prompt
        prompt = PromptTemplate.format_rag_prompt(query, context)
        
        # Generate response
        try:
            answer = self.llm.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=512
            )
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return self._create_error_response(query, "Generation error occurred")
        
        # Validate response
        is_valid = True
        if self.enable_safety_filter:
            is_valid, answer = SafetyFilter.validate_response(answer, context, strict=True)
            if not is_valid:
                logger.warning("Response failed safety validation")
        
        # Build response
        response = RAGResponse(
            query=query,
            answer=answer,
            sources=retrieval_results,
            classification=response_classification,
            timestamp=datetime.utcnow().isoformat(),
            metadata={
                "retrieved_count": len(retrieval_results),
                "avg_similarity": sum(r.score for r in retrieval_results) / len(retrieval_results),
                "min_similarity": min(r.score for r in retrieval_results),
                "max_similarity": max(r.score for r in retrieval_results),
            },
            is_valid=is_valid
        )
        
        logger.info(f"Query processed successfully. Classification: {response_classification.name}")
        return response
    
    def _determine_classification(self, results: List[RetrievalResult]) -> ClassificationLevel:
        """Determine classification level from retrieved documents"""
        if not results:
            return self.default_classification
        
        max_classification = self.default_classification
        for result in results:
            doc_classification = ClassificationLevel[result.metadata.get("classification", "UNCLASSIFIED")]
            if doc_classification > max_classification:
                max_classification = doc_classification
        
        return max_classification
    
    def _create_error_response(self, query: str, error_message: str) -> RAGResponse:
        """Create error response"""
        return RAGResponse(
            query=query,
            answer=f"Error: {error_message}",
            sources=[],
            classification=self.default_classification,
            timestamp=datetime.utcnow().isoformat(),
            metadata={"error": error_message},
            is_valid=False
        )
    
    def _create_access_denied_response(self,
                                      query: str,
                                      user_clearance: ClassificationLevel,
                                      required_clearance: ClassificationLevel) -> RAGResponse:
        """Create access denied response"""
        message = (
            f"ACCESS DENIED: Documents are classified as {required_clearance.name}. "
            f"Your clearance level: {user_clearance.name}."
        )
        
        return RAGResponse(
            query=query,
            answer=message,
            sources=[],
            classification=required_clearance,
            timestamp=datetime.utcnow().isoformat(),
            metadata={
                "user_clearance": user_clearance.name,
                "required_clearance": required_clearance.name
            },
            is_valid=False
        )


class BatchRAGPipeline(RAGPipeline):
    """
    Process multiple queries in batch
    """
    
    def batch_query(self,
                   queries: List[str],
                   **kwargs) -> List[RAGResponse]:
        """
        Process multiple queries
        
        Args:
            queries: List of queries
            **kwargs: Additional arguments for query()
        
        Returns:
            List of RAGResponse objects
        """
        logger.info(f"Processing {len(queries)} queries in batch")
        
        responses = []
        for query in queries:
            try:
                response = self.query(query, **kwargs)
                responses.append(response)
            except Exception as e:
                logger.error(f"Failed to process query '{query}': {e}")
                responses.append(self._create_error_response(query, str(e)))
        
        return responses


def format_response_for_display(response: RAGResponse, include_sources: bool = True) -> str:
    """
    Format RAG response for display
    
    Args:
        response: RAGResponse object
        include_sources: Include source documents
    
    Returns:
        Formatted string
    """
    lines = []
    
    # Classification warning
    if response.classification != ClassificationLevel.UNCLASSIFIED:
        lines.append("=" * 60)
        lines.append(f"CLASSIFICATION: {response.classification.name}")
        lines.append("=" * 60)
        lines.append("")
    
    # Query
    lines.append(f"QUERY: {response.query}")
    lines.append("")
    
    # Answer
    lines.append("ANSWER:")
    lines.append(response.answer)
    lines.append("")
    
    # Sources
    if include_sources and response.sources:
        lines.append("SOURCES:")
        for result in response.sources:
            source_file = result.metadata.get("source_file", "Unknown")
            similarity = result.score
            lines.append(f"  - {source_file} (relevance: {similarity:.3f})")
        lines.append("")
    
    # Metadata
    if response.metadata:
        lines.append(f"Retrieved: {response.metadata.get('retrieved_count', 0)} documents")
        if 'avg_similarity' in response.metadata:
            lines.append(f"Avg Similarity: {response.metadata['avg_similarity']:.3f}")
    
    lines.append("")
    lines.append(f"Timestamp: {response.timestamp}")
    
    if response.classification != ClassificationLevel.UNCLASSIFIED:
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"END {response.classification.name}")
        lines.append("=" * 60)
    
    return "\n".join(lines)
