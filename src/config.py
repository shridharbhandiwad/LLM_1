"""
Configuration Management for Offline Private LLM-RAG System
Handles all system configuration with security defaults
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ClassificationLevel(Enum):
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3
    
    def __lt__(self, other):
        return self.value < other.value
    
    def __le__(self, other):
        return self.value <= other.value


@dataclass
class SystemConfig:
    """Main system configuration"""
    
    # System Identity
    system_name: str = "DEFENSE_RAG_SYSTEM"
    environment: Environment = Environment.PRODUCTION
    
    # Paths (all must be local)
    # Use paths relative to project root (works on both Unix and Windows)
    base_path: Path = Path(__file__).parent.parent.resolve()
    model_path: Path = Path(__file__).parent.parent.resolve() / "models"
    data_path: Path = Path(__file__).parent.parent.resolve() / "data"
    log_path: Path = Path(__file__).parent.parent.resolve() / "logs"
    
    # Embedding Model
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_model_path: Optional[Path] = None
    embedding_dimension: int = 384
    
    # LLM Model
    llm_model_name: str = "llama-3.2-3b-instruct"
    llm_model_path: Optional[Path] = None
    llm_max_tokens: int = 512
    llm_temperature: float = 0.1
    llm_context_length: int = 4096
    llm_threads: int = 8
    
    # Vector Database
    vector_db_path: Optional[Path] = None
    metadata_db_path: Optional[Path] = None
    
    # Chunking Strategy
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Retrieval
    top_k: int = 5
    similarity_threshold: float = 0.7
    
    # Security
    enable_encryption: bool = True
    encryption_key_path: Optional[Path] = None
    enable_rbac: bool = True
    enable_audit_log: bool = True
    audit_log_path: Optional[Path] = None
    
    # Classification
    default_classification: ClassificationLevel = ClassificationLevel.UNCLASSIFIED
    enforce_classification: bool = True
    
    # Network Isolation
    disable_network: bool = True
    localhost_only: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    # Performance
    max_concurrent_queries: int = 5
    query_timeout: int = 30
    
    def __post_init__(self):
        """Initialize paths"""
        if self.embedding_model_path is None:
            self.embedding_model_path = self.model_path / "embeddings" / self.embedding_model_name
        
        if self.llm_model_path is None:
            self.llm_model_path = self.model_path / "llm" / f"{self.llm_model_name}.gguf"
        
        if self.vector_db_path is None:
            self.vector_db_path = self.data_path / "vectors"
        
        if self.metadata_db_path is None:
            self.metadata_db_path = self.data_path / "metadata.db"
        
        if self.audit_log_path is None:
            self.audit_log_path = self.log_path / "audit.log"
        
        if self.encryption_key_path is None:
            self.encryption_key_path = self.data_path / "keys" / "master.key"
    
    def verify_offline_mode(self) -> bool:
        """Verify system is in offline mode"""
        if self.disable_network:
            # Check if network is actually disabled
            # This is a placeholder - actual implementation would check firewall rules
            return True
        return False
    
    def create_directories(self):
        """Create all required directories"""
        dirs = [
            self.base_path,
            self.model_path,
            self.model_path / "embeddings",
            self.model_path / "llm",
            self.data_path,
            self.data_path / "documents",
            self.data_path / "processed",
            self.data_path / "keys",
            self.vector_db_path,
            self.log_path
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            # Secure permissions: owner only (Unix-like systems only)
            # Windows doesn't use Unix permissions, so skip on Windows
            if os.name != 'nt':
                os.chmod(dir_path, 0o700)


def load_config() -> SystemConfig:
    """Load configuration from environment or defaults"""
    config = SystemConfig()
    
    # Override from environment variables
    if env_val := os.getenv("EMBEDDING_MODEL_PATH"):
        config.embedding_model_path = Path(env_val)
    
    if env_val := os.getenv("LLM_MODEL_PATH"):
        config.llm_model_path = Path(env_val)
    
    if env_val := os.getenv("VECTOR_DB_PATH"):
        config.vector_db_path = Path(env_val)
    
    if env_val := os.getenv("TOP_K_RETRIEVAL"):
        config.top_k = int(env_val)
    
    if env_val := os.getenv("CHUNK_SIZE"):
        config.chunk_size = int(env_val)
    
    if env_val := os.getenv("USE_ENCRYPTION"):
        config.enable_encryption = env_val.lower() == "true"
    
    return config


# Global config instance
config = load_config()
