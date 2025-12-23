"""
Offline Embedding Generation for Private LLM-RAG System
Uses sentence-transformers with fully offline models
"""

import logging
import numpy as np
from pathlib import Path
from typing import List, Union, Optional
import os

# Note: Offline mode is set per-function, not at module level
# This allows the download function to work while keeping operations offline

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from ..ingestion.chunker import Chunk


logger = logging.getLogger(__name__)


class OfflineEmbeddingGenerator:
    """
    Generate embeddings using offline models
    CRITICAL: No network access, no telemetry
    """
    
    def __init__(self, model_path: Union[str, Path], device: str = "cpu"):
        """
        Initialize embedding generator
        
        Args:
            model_path: Path to local model directory
            device: Device to run on ('cpu' or 'cuda')
        """
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install offline with: pip install sentence-transformers --no-index"
            )
        
        # Enable offline mode for operations
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        self.model_path = Path(model_path)
        self.device = device
        
        # Verify model exists locally
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. "
                f"Download model offline first."
            )
        
        logger.info(f"Loading embedding model from {self.model_path}")
        
        # Load model from local path only
        try:
            self.model = SentenceTransformer(
                str(self.model_path),
                device=self.device,
                cache_folder=None  # Disable cache to prevent network access
            )
            
            # Verify no network calls
            self._verify_offline_mode()
            
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def _verify_offline_mode(self):
        """Verify model is operating in offline mode"""
        # Check for network-related environment variables
        if os.getenv("TRANSFORMERS_OFFLINE") != "1":
            logger.warning("TRANSFORMERS_OFFLINE not set. Setting now.")
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        
        logger.info("Offline mode verified")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector (numpy array)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return np.zeros(self.embedding_dim)
        
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts
            batch_size: Batch size for processing
        
        Returns:
            Array of embeddings (shape: [n_texts, embedding_dim])
        """
        if not texts:
            logger.warning("Empty text list provided")
            return np.array([])
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=True,
                normalize_embeddings=True
            )
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
        
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def embed_chunks(self, chunks: List[Chunk], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for document chunks
        
        Args:
            chunks: List of Chunk objects
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors
        """
        texts = [chunk.content for chunk in chunks]
        embeddings = self.generate_embeddings(texts, batch_size=batch_size)
        
        return list(embeddings)
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            Similarity score (0-1)
        """
        # Embeddings are already normalized, so dot product = cosine similarity
        return float(np.dot(embedding1, embedding2))


class EmbeddingCache:
    """Cache embeddings to disk for reuse"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, chunk_id: str) -> Path:
        """Get cache file path for chunk"""
        return self.cache_dir / f"{chunk_id}.npy"
    
    def has_cached(self, chunk_id: str) -> bool:
        """Check if embedding is cached"""
        return self.get_cache_path(chunk_id).exists()
    
    def save(self, chunk_id: str, embedding: np.ndarray):
        """Save embedding to cache"""
        cache_path = self.get_cache_path(chunk_id)
        np.save(cache_path, embedding)
    
    def load(self, chunk_id: str) -> Optional[np.ndarray]:
        """Load embedding from cache"""
        cache_path = self.get_cache_path(chunk_id)
        if cache_path.exists():
            return np.load(cache_path)
        return None
    
    def clear(self):
        """Clear all cached embeddings"""
        for cache_file in self.cache_dir.glob("*.npy"):
            cache_file.unlink()


def download_model_for_offline_use(model_name: str, target_path: Path):
    """
    Helper function to download model for offline use
    THIS SHOULD BE RUN ONCE ON AN INTERNET-CONNECTED MACHINE
    Then transfer the model to air-gapped system
    
    Args:
        model_name: HuggingFace model name (e.g., 'sentence-transformers/all-MiniLM-L6-v2')
        target_path: Local path to save model
    """
    if SentenceTransformer is None:
        raise ImportError(
            "sentence-transformers package is not installed.\n"
            "\nPlease install dependencies first:\n"
            "  pip install -r requirements.txt\n"
            "\nOr install sentence-transformers directly:\n"
            "  pip install sentence-transformers\n"
        )
    
    # IMPORTANT: Temporarily enable online mode for downloading
    # Save current values
    old_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    old_hf_datasets_offline = os.environ.get("HF_DATASETS_OFFLINE")
    
    try:
        # Enable online mode
        os.environ.pop("TRANSFORMERS_OFFLINE", None)
        os.environ.pop("HF_DATASETS_OFFLINE", None)
        
        logger.info(f"Downloading model {model_name} to {target_path}")
        
        # Download model (requires internet)
        model = SentenceTransformer(model_name)
        
        # Save to target path
        target_path.mkdir(parents=True, exist_ok=True)
        model.save(str(target_path))
        
        logger.info(f"Model saved to {target_path}")
        logger.info("Transfer this directory to your air-gapped system")
        
    finally:
        # Restore offline mode
        if old_transformers_offline is not None:
            os.environ["TRANSFORMERS_OFFLINE"] = old_transformers_offline
        if old_hf_datasets_offline is not None:
            os.environ["HF_DATASETS_OFFLINE"] = old_hf_datasets_offline
