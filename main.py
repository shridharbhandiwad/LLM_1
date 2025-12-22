#!/usr/bin/env python3
"""
Main Application for Offline Private LLM-RAG System
Defense-grade air-gapped AI system
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import config, ClassificationLevel
from src.ingestion import DocumentLoader, RadarLogLoader, DocumentChunker
from src.embedding import OfflineEmbeddingGenerator
from src.vectordb import EncryptedVectorStore, MetadataDatabase
from src.retrieval import SemanticRetriever, format_context
from src.llm import OfflineLLM, PromptTemplate
from src.orchestration import RAGPipeline, format_response_for_display
from src.security import AuditLogger, RBACManager, NetworkIsolationVerifier


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.log_path / "system.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class OfflineRAGSystem:
    """
    Complete offline RAG system
    """
    
    def __init__(self):
        self.config = config
        self.initialized = False
        
        # Components
        self.embedding_generator = None
        self.vector_store = None
        self.metadata_db = None
        self.llm = None
        self.retriever = None
        self.pipeline = None
        self.audit_logger = None
        self.rbac = None
    
    def verify_security(self) -> bool:
        """Verify security requirements"""
        logger.info("=" * 60)
        logger.info("SECURITY VERIFICATION")
        logger.info("=" * 60)
        
        # Check network isolation
        if self.config.disable_network:
            results = NetworkIsolationVerifier.verify_all()
            
            for check in results["checks"]:
                status = "✓" if check["passed"] else "✗"
                logger.info(f"{status} {check['name']}: {check['details']}")
            
            if not results["all_passed"]:
                logger.warning("Some security checks failed. Proceed with caution.")
                return False
        
        logger.info("✓ Security verification completed")
        return True
    
    def initialize(self, skip_llm: bool = False):
        """
        Initialize all system components
        
        Args:
            skip_llm: Skip LLM initialization (for testing without model)
        """
        logger.info("=" * 60)
        logger.info("INITIALIZING OFFLINE RAG SYSTEM")
        logger.info("=" * 60)
        
        # Create directories
        self.config.create_directories()
        
        # Initialize security components
        logger.info("Initializing security components...")
        self.audit_logger = AuditLogger(
            self.config.audit_log_path,
            enable_encryption=self.config.enable_encryption
        )
        
        self.rbac = RBACManager()
        self._setup_default_users()
        
        # Initialize embedding generator
        logger.info("Initializing embedding generator...")
        try:
            self.embedding_generator = OfflineEmbeddingGenerator(
                model_path=self.config.embedding_model_path,
                device="cpu"
            )
            logger.info("✓ Embedding generator ready")
        except Exception as e:
            logger.error(f"Failed to initialize embedding generator: {e}")
            logger.info("To use the system, download the model first:")
            logger.info(f"  python scripts/download_models.py")
            raise
        
        # Initialize vector store
        logger.info("Initializing vector database...")
        self.vector_store = EncryptedVectorStore(
            dimension=self.config.embedding_dimension,
            index_path=self.config.vector_db_path,
            encryption_key=None  # Will generate new key
        )
        
        # Try to load existing index
        try:
            self.vector_store.load()
            logger.info(f"✓ Loaded existing index: {self.vector_store.index.ntotal} vectors")
        except FileNotFoundError:
            logger.info("No existing index found. Will create new index.")
        
        # Initialize metadata database
        logger.info("Initializing metadata database...")
        self.metadata_db = MetadataDatabase(self.config.metadata_db_path)
        logger.info("✓ Metadata database ready")
        
        # Initialize LLM
        if not skip_llm:
            logger.info("Initializing LLM...")
            try:
                self.llm = OfflineLLM(
                    model_path=self.config.llm_model_path,
                    n_ctx=self.config.llm_context_length,
                    n_threads=self.config.llm_threads,
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens
                )
                logger.info("✓ LLM ready")
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                logger.info("To use the system, download the model first:")
                logger.info(f"  Download a GGUF model and place at: {self.config.llm_model_path}")
                raise
        
        # Initialize retriever
        logger.info("Initializing retriever...")
        self.retriever = SemanticRetriever(
            vector_store=self.vector_store,
            embedding_generator=self.embedding_generator,
            metadata_db=self.metadata_db
        )
        logger.info("✓ Retriever ready")
        
        # Initialize RAG pipeline
        if not skip_llm and self.llm:
            logger.info("Initializing RAG pipeline...")
            self.pipeline = RAGPipeline(
                retriever=self.retriever,
                llm=self.llm,
                default_classification=self.config.default_classification,
                enable_safety_filter=True
            )
            logger.info("✓ RAG pipeline ready")
        
        self.initialized = True
        logger.info("=" * 60)
        logger.info("SYSTEM INITIALIZATION COMPLETE")
        logger.info("=" * 60)
    
    def _setup_default_users(self):
        """Setup default users for testing"""
        self.rbac.add_user("admin", roles=["ADMIN"])
        self.rbac.add_user("analyst_ts", roles=["ANALYST_TS"])
        self.rbac.add_user("analyst_s", roles=["ANALYST_S"])
        self.rbac.add_user("operator", roles=["OPERATOR"])
        
        logger.info("✓ Default users configured")
    
    def ingest_documents(self, document_path: Path, user_id: str = "admin"):
        """
        Ingest documents into the system
        
        Args:
            document_path: Path to document or directory
            user_id: User performing ingestion
        """
        if not self.initialized:
            raise RuntimeError("System not initialized")
        
        # Check permissions
        if not self.rbac.check_permission(user_id, "ingest_documents"):
            logger.error(f"User {user_id} does not have ingestion permission")
            return
        
        logger.info(f"Ingesting documents from: {document_path}")
        
        # Load documents
        if document_path.suffix == ".dat":
            loader = RadarLogLoader()
        else:
            loader = DocumentLoader()
        
        if document_path.is_dir():
            documents = loader.load_directory(document_path)
        else:
            documents = [loader.load(document_path)]
        
        logger.info(f"Loaded {len(documents)} documents")
        
        # Chunk documents
        chunker = DocumentChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        chunks = chunker.chunk_documents(documents)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        embeddings = self.embedding_generator.embed_chunks(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Add to vector store
        import numpy as np
        self.vector_store.add_vectors(np.array(embeddings), chunks)
        logger.info("✓ Added to vector store")
        
        # Add to metadata database
        self.metadata_db.insert_chunks(chunks)
        logger.info("✓ Added to metadata database")
        
        # Save index
        self.vector_store.save()
        logger.info("✓ Saved index")
        
        # Audit log
        for doc in documents:
            self.audit_logger.log_document_ingest(
                user_id=user_id,
                doc_id=doc.doc_id,
                classification=ClassificationLevel[doc.metadata["classification"]],
                success=True
            )
        
        logger.info(f"✓ Ingestion complete: {len(documents)} documents, {len(chunks)} chunks")
    
    def query(self, query_text: str, user_id: str = "analyst_ts",
             top_k: Optional[int] = None) -> str:
        """
        Query the RAG system
        
        Args:
            query_text: User query
            user_id: User identifier
            top_k: Number of results to retrieve
        
        Returns:
            Formatted response
        """
        if not self.initialized or not self.pipeline:
            raise RuntimeError("System not initialized or LLM not available")
        
        # Check permissions
        if not self.rbac.check_permission(user_id, "query_system"):
            logger.error(f"User {user_id} does not have query permission")
            return "ACCESS DENIED: Insufficient permissions"
        
        # Get user clearance
        user_clearance = self.rbac.get_user_clearance(user_id)
        
        # Execute query
        logger.info(f"Processing query from {user_id}: {query_text[:50]}...")
        
        response = self.pipeline.query(
            query=query_text,
            top_k=top_k or self.config.top_k,
            similarity_threshold=self.config.similarity_threshold,
            user_classification=user_clearance
        )
        
        # Audit log
        self.audit_logger.log_query(
            user_id=user_id,
            query=query_text,
            classification=response.classification,
            retrieved_docs=response.sources,
            success=response.is_valid
        )
        
        return format_response_for_display(response)
    
    def shutdown(self):
        """Shutdown system"""
        logger.info("Shutting down system...")
        
        if self.metadata_db:
            self.metadata_db.close()
        
        logger.info("✓ System shutdown complete")


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("OFFLINE PRIVATE LLM-RAG SYSTEM")
    print("Defense-Grade Air-Gapped AI")
    print("=" * 60 + "\n")
    
    # Initialize system
    system = OfflineRAGSystem()
    
    # Verify security
    system.verify_security()
    
    try:
        # Initialize (skip LLM for demo if model not available)
        try:
            system.initialize(skip_llm=False)
        except Exception as e:
            logger.warning(f"Full initialization failed: {e}")
            logger.info("Initializing without LLM for ingestion only...")
            system.initialize(skip_llm=True)
        
        # Check if we have documents to ingest
        doc_path = config.data_path / "documents"
        if doc_path.exists() and list(doc_path.glob("*")):
            logger.info(f"\nFound documents in {doc_path}")
            
            response = input("Ingest documents? (y/n): ")
            if response.lower() == 'y':
                system.ingest_documents(doc_path, user_id="admin")
        
        # Interactive query loop
        if system.pipeline:
            print("\n" + "=" * 60)
            print("QUERY INTERFACE")
            print("=" * 60)
            print("Enter queries (or 'quit' to exit)")
            print()
            
            while True:
                try:
                    query = input("\nQuery> ").strip()
                    
                    if query.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    if not query:
                        continue
                    
                    # Process query
                    result = system.query(query, user_id="analyst_ts")
                    print("\n" + result + "\n")
                
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Query failed: {e}")
        
    finally:
        system.shutdown()
    
    print("\nSystem terminated.")


if __name__ == "__main__":
    main()
