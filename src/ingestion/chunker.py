"""
Document Chunking for Offline Private LLM-RAG System
Implements recursive character-based chunking with overlap
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass
import re

from .document_loader import Document


logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a document chunk"""
    chunk_id: str
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    chunk_index: int


class DocumentChunker:
    """Chunk documents into smaller pieces for embedding"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target size in tokens (approximate as characters * 0.25)
            chunk_overlap: Overlap size in tokens
        """
        self.chunk_size = chunk_size * 4  # Convert tokens to approximate characters
        self.chunk_overlap = chunk_overlap * 4
        
        # Splitting separators in order of preference
        self.separators = [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentences
            "? ",
            "! ",
            "; ",
            ": ",
            ", ",
            " ",     # Words
            ""       # Characters (last resort)
        ]
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Split document into chunks
        
        Args:
            document: Document to chunk
        
        Returns:
            List of Chunk objects
        """
        logger.info(f"Chunking document {document.doc_id} ({len(document.content)} chars)")
        
        # Split text recursively
        text_chunks = self._recursive_split(document.content)
        
        # Create Chunk objects with metadata
        chunks = []
        for idx, text in enumerate(text_chunks):
            chunk = Chunk(
                chunk_id=f"{document.doc_id}_chunk_{idx}",
                doc_id=document.doc_id,
                content=text,
                metadata={
                    **document.metadata,  # Inherit document metadata
                    "chunk_index": idx,
                    "chunk_count": len(text_chunks),
                    "chunk_size": len(text)
                },
                chunk_index=idx
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from document {document.doc_id}")
        return chunks
    
    def _recursive_split(self, text: str, separators: List[str] = None) -> List[str]:
        """
        Recursively split text using separators
        
        Args:
            text: Text to split
            separators: List of separators to try
        
        Returns:
            List of text chunks
        """
        if separators is None:
            separators = self.separators
        
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        
        # Try each separator
        separator = separators[0] if separators else ""
        
        if separator:
            splits = text.split(separator)
        else:
            # Last resort: split by character
            splits = list(text)
        
        # Merge small splits and handle overlap
        chunks = []
        current_chunk = []
        current_size = 0
        
        for split in splits:
            split_size = len(split) + len(separator)
            
            # If adding this split exceeds chunk size
            if current_size + split_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = separator.join(current_chunk)
                chunks.append(chunk_text)
                
                # Start new chunk with overlap
                overlap_size = 0
                overlap_parts = []
                
                # Add parts from end of current chunk for overlap
                for part in reversed(current_chunk):
                    part_size = len(part) + len(separator)
                    if overlap_size + part_size <= self.chunk_overlap:
                        overlap_parts.insert(0, part)
                        overlap_size += part_size
                    else:
                        break
                
                current_chunk = overlap_parts
                current_size = overlap_size
            
            current_chunk.append(split)
            current_size += split_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(separator.join(current_chunk))
        
        # Recursively split chunks that are still too large
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size and len(separators) > 1:
                # Try next separator
                sub_chunks = self._recursive_split(chunk, separators[1:])
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """
        Chunk multiple documents
        
        Args:
            documents: List of documents
        
        Returns:
            List of all chunks
        """
        all_chunks = []
        for document in documents:
            chunks = self.chunk_document(document)
            all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} total chunks from {len(documents)} documents")
        return all_chunks


class SemanticChunker(DocumentChunker):
    """
    Advanced chunker that attempts to preserve semantic boundaries
    Uses sentence boundaries and paragraph structure
    """
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        super().__init__(chunk_size, chunk_overlap)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (can be enhanced with NLTK if needed)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """Chunk document preserving semantic boundaries"""
        
        # Split into paragraphs first
        paragraphs = document.content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_idx = 0
        
        for paragraph in paragraphs:
            sentences = self._split_into_sentences(paragraph)
            
            for sentence in sentences:
                sentence_size = len(sentence)
                
                if current_size + sentence_size > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = ' '.join(current_chunk)
                    chunk = Chunk(
                        chunk_id=f"{document.doc_id}_chunk_{chunk_idx}",
                        doc_id=document.doc_id,
                        content=chunk_text,
                        metadata={
                            **document.metadata,
                            "chunk_index": chunk_idx,
                            "chunk_size": len(chunk_text)
                        },
                        chunk_index=chunk_idx
                    )
                    chunks.append(chunk)
                    chunk_idx += 1
                    
                    # Start new chunk with overlap (last few sentences)
                    overlap_text = ' '.join(current_chunk[-3:])  # Last 3 sentences
                    current_chunk = [overlap_text] if len(overlap_text) <= self.chunk_overlap else []
                    current_size = len(overlap_text)
                
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk = Chunk(
                chunk_id=f"{document.doc_id}_chunk_{chunk_idx}",
                doc_id=document.doc_id,
                content=chunk_text,
                metadata={
                    **document.metadata,
                    "chunk_index": chunk_idx,
                    "chunk_size": len(chunk_text)
                },
                chunk_index=chunk_idx
            )
            chunks.append(chunk)
        
        # Update chunk counts
        for chunk in chunks:
            chunk.metadata["chunk_count"] = len(chunks)
        
        logger.info(f"Created {len(chunks)} semantic chunks from document {document.doc_id}")
        return chunks
