"""
FAISS Vector Store with Encryption for Offline Private LLM-RAG System
Provides secure, encrypted vector storage and similarity search
"""

import logging
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sqlite3
import json

try:
    import faiss
except ImportError:
    faiss = None

from ..ingestion.chunker import Chunk
from ..config import ClassificationLevel


logger = logging.getLogger(__name__)


class VectorStore:
    """
    FAISS-based vector store with metadata filtering
    Uses exact search (IndexFlatIP) for security and reproducibility
    """
    
    def __init__(self, dimension: int, index_path: Optional[Path] = None):
        """
        Initialize vector store
        
        Args:
            dimension: Embedding dimension
            index_path: Path to save/load index
        """
        if faiss is None:
            raise ImportError("faiss not installed. Install with: pip install faiss-cpu")
        
        self.dimension = dimension
        self.index_path = index_path
        
        # Create FAISS index (Inner Product for normalized vectors = cosine similarity)
        self.index = faiss.IndexFlatIP(dimension)
        
        # Store metadata separately (FAISS doesn't store metadata)
        self.metadata: List[Dict[str, Any]] = []
        self.chunk_ids: List[str] = []
        
        logger.info(f"Initialized VectorStore with dimension {dimension}")
    
    def add_vectors(self, embeddings: np.ndarray, chunks: List[Chunk]):
        """
        Add vectors to the index
        
        Args:
            embeddings: Embedding vectors (shape: [n, dimension])
            chunks: Corresponding chunk objects
        """
        if len(embeddings) != len(chunks):
            raise ValueError("Number of embeddings must match number of chunks")
        
        # Ensure correct shape and type
        embeddings = embeddings.astype('float32')
        
        # Normalize vectors for cosine similarity via inner product
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Store metadata
        for chunk in chunks:
            self.metadata.append(chunk.metadata)
            self.chunk_ids.append(chunk.chunk_id)
        
        logger.info(f"Added {len(chunks)} vectors to index. Total: {self.index.ntotal}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5,
               classification_filter: Optional[ClassificationLevel] = None,
               metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            classification_filter: Filter by maximum classification level
            metadata_filters: Additional metadata filters
        
        Returns:
            List of results with scores and metadata
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty")
            return []
        
        # Prepare query
        query = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query)
        
        # Search (retrieve more if filtering)
        search_k = min(top_k * 3, self.index.ntotal)  # Get more for filtering
        distances, indices = self.index.search(query, search_k)
        
        # Build results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            metadata = self.metadata[idx]
            chunk_id = self.chunk_ids[idx]
            
            # Apply filters
            if not self._passes_filters(metadata, classification_filter, metadata_filters):
                continue
            
            results.append({
                "chunk_id": chunk_id,
                "score": float(distance),  # Cosine similarity (0-1)
                "metadata": metadata
            })
            
            if len(results) >= top_k:
                break
        
        logger.info(f"Found {len(results)} results (filtered from {search_k})")
        return results
    
    def _passes_filters(self, metadata: Dict[str, Any],
                       classification_filter: Optional[ClassificationLevel],
                       metadata_filters: Optional[Dict[str, Any]]) -> bool:
        """Check if metadata passes filters"""
        
        # Classification filter
        if classification_filter is not None:
            doc_classification = ClassificationLevel[metadata.get("classification", "UNCLASSIFIED")]
            if doc_classification > classification_filter:
                return False
        
        # Custom metadata filters
        if metadata_filters:
            for key, value in metadata_filters.items():
                if metadata.get(key) != value:
                    return False
        
        return True
    
    def save(self, path: Optional[Path] = None):
        """Save index to disk"""
        save_path = path or self.index_path
        if save_path is None:
            raise ValueError("No save path specified")
        
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_file = save_path / "index.faiss"
        faiss.write_index(self.index, str(index_file))
        
        # Save metadata
        metadata_file = save_path / "metadata.pkl"
        with open(metadata_file, 'wb') as f:
            pickle.dump({
                "metadata": self.metadata,
                "chunk_ids": self.chunk_ids,
                "dimension": self.dimension
            }, f)
        
        logger.info(f"Saved index to {save_path}")
    
    def load(self, path: Optional[Path] = None):
        """Load index from disk"""
        load_path = path or self.index_path
        if load_path is None:
            raise ValueError("No load path specified")
        
        load_path = Path(load_path)
        
        # Load FAISS index
        index_file = load_path / "index.faiss"
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")
        
        self.index = faiss.read_index(str(index_file))
        
        # Load metadata
        metadata_file = load_path / "metadata.pkl"
        with open(metadata_file, 'rb') as f:
            data = pickle.load(f)
            self.metadata = data["metadata"]
            self.chunk_ids = data["chunk_ids"]
            self.dimension = data["dimension"]
        
        logger.info(f"Loaded index from {load_path}. Total vectors: {self.index.ntotal}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": "IndexFlatIP",
            "metadata_count": len(self.metadata)
        }


class EncryptedVectorStore(VectorStore):
    """
    Vector store with AES-256 encryption at rest
    """
    
    def __init__(self, dimension: int, index_path: Optional[Path] = None,
                 encryption_key: Optional[bytes] = None):
        """
        Initialize encrypted vector store
        
        Args:
            dimension: Embedding dimension
            index_path: Path to save/load index
            encryption_key: 32-byte encryption key (AES-256)
        """
        super().__init__(dimension, index_path)
        
        if encryption_key is None:
            # Generate key if not provided
            import secrets
            encryption_key = secrets.token_bytes(32)
            logger.warning("Generated new encryption key. Save this securely!")
        
        if len(encryption_key) != 32:
            raise ValueError("Encryption key must be 32 bytes for AES-256")
        
        self.encryption_key = encryption_key
    
    def _encrypt(self, data: bytes) -> bytes:
        """Encrypt data using AES-256-GCM"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import os
        
        aesgcm = AESGCM(self.encryption_key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # Prepend nonce to ciphertext
        return nonce + ciphertext
    
    def _decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using AES-256-GCM"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        # Extract nonce and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        aesgcm = AESGCM(self.encryption_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    def save(self, path: Optional[Path] = None):
        """Save encrypted index to disk"""
        save_path = path or self.index_path
        if save_path is None:
            raise ValueError("No save path specified")
        
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index to bytes
        index_bytes = faiss.serialize_index(self.index)
        encrypted_index = self._encrypt(index_bytes)
        
        index_file = save_path / "index.faiss.enc"
        with open(index_file, 'wb') as f:
            f.write(encrypted_index)
        
        # Save metadata
        metadata_bytes = pickle.dumps({
            "metadata": self.metadata,
            "chunk_ids": self.chunk_ids,
            "dimension": self.dimension
        })
        encrypted_metadata = self._encrypt(metadata_bytes)
        
        metadata_file = save_path / "metadata.pkl.enc"
        with open(metadata_file, 'wb') as f:
            f.write(encrypted_metadata)
        
        logger.info(f"Saved encrypted index to {save_path}")
    
    def load(self, path: Optional[Path] = None):
        """Load encrypted index from disk"""
        load_path = path or self.index_path
        if load_path is None:
            raise ValueError("No load path specified")
        
        load_path = Path(load_path)
        
        # Load and decrypt FAISS index
        index_file = load_path / "index.faiss.enc"
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")
        
        with open(index_file, 'rb') as f:
            encrypted_index = f.read()
        
        index_bytes = self._decrypt(encrypted_index)
        self.index = faiss.deserialize_index(index_bytes)
        
        # Load and decrypt metadata
        metadata_file = load_path / "metadata.pkl.enc"
        with open(metadata_file, 'rb') as f:
            encrypted_metadata = f.read()
        
        metadata_bytes = self._decrypt(encrypted_metadata)
        data = pickle.loads(metadata_bytes)
        
        self.metadata = data["metadata"]
        self.chunk_ids = data["chunk_ids"]
        self.dimension = data["dimension"]
        
        logger.info(f"Loaded encrypted index from {load_path}. Total vectors: {self.index.ntotal}")


class MetadataDatabase:
    """
    SQLite database for storing chunk metadata with full-text search
    """
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                classification TEXT NOT NULL,
                source_file TEXT,
                document_type TEXT,
                chunk_index INTEGER,
                chunk_count INTEGER,
                ingest_date TEXT,
                metadata_json TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_doc_id ON chunks(doc_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_classification ON chunks(classification)
        """)
        
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(content, source_file, content=chunks, content_rowid=rowid)
        """)
        
        self.conn.commit()
    
    def insert_chunks(self, chunks: List[Chunk]):
        """Insert chunks into database"""
        cursor = self.conn.cursor()
        
        for chunk in chunks:
            cursor.execute("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, doc_id, content, classification, source_file, document_type,
                 chunk_index, chunk_count, ingest_date, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.chunk_id,
                chunk.doc_id,
                chunk.content,
                chunk.metadata.get("classification", "UNCLASSIFIED"),
                chunk.metadata.get("source_file"),
                chunk.metadata.get("document_type"),
                chunk.metadata.get("chunk_index"),
                chunk.metadata.get("chunk_count"),
                chunk.metadata.get("ingest_date"),
                json.dumps(chunk.metadata)
            ))
        
        self.conn.commit()
        logger.info(f"Inserted {len(chunks)} chunks into metadata database")
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chunk by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def search_text(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search in chunks"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT chunks.* FROM chunks_fts
            JOIN chunks ON chunks.rowid = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            LIMIT ?
        """, (query, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        self.conn.close()
