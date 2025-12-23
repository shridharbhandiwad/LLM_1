#!/usr/bin/env python3
"""
Example Usage Script for Offline Private LLM-RAG System
Demonstrates key functionality with sample data
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ingestion import DocumentLoader, DocumentChunker
from src.config import ClassificationLevel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_load_documents():
    """Example 1: Load and chunk documents"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Load and Chunk Documents")
    print("=" * 60 + "\n")
    
    # Load a document
    loader = DocumentLoader()
    doc = loader.load(
        Path("data/documents/unclassified_sop.txt"),
        classification=ClassificationLevel.UNCLASSIFIED
    )
    
    print(f"Loaded document: {doc.doc_id}")
    print(f"Content length: {len(doc.content)} characters")
    print(f"Classification: {doc.metadata['classification']}")
    print(f"Checksum: {doc.metadata['checksum'][:16]}...")
    
    # Chunk the document
    chunker = DocumentChunker(chunk_size=512, chunk_overlap=50)
    chunks = chunker.chunk_document(doc)
    
    print(f"\nCreated {len(chunks)} chunks")
    print(f"\nFirst chunk preview:")
    print(chunks[0].content[:200] + "...")


def example_2_radar_logs():
    """Example 2: Load radar log files"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Load Radar Logs")
    print("=" * 60 + "\n")
    
    from src.ingestion import RadarLogLoader
    
    loader = RadarLogLoader()
    doc = loader.load(
        Path("data/documents/radar_track_log.dat"),
        classification=ClassificationLevel.SECRET
    )
    
    print(f"Loaded radar log: {doc.doc_id}")
    print(f"Classification: {doc.metadata['classification']}")
    print(f"\nSample tracks:")
    print(doc.content[:300] + "...")


def example_3_security_features():
    """Example 3: Security and access control"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Security Features")
    print("=" * 60 + "\n")
    
    from src.security import RBACManager, AuditLogger
    from pathlib import Path
    
    # Setup RBAC
    rbac = RBACManager()
    rbac.add_user("admin1", roles=["ADMIN"])
    rbac.add_user("analyst1", roles=["ANALYST_TS"])
    rbac.add_user("operator1", roles=["OPERATOR"])
    
    print("Users configured:")
    for user_id, user in rbac.users.items():
        print(f"  {user_id}: roles={user.roles}, clearance={user.clearance.name}")
    
    # Test permissions
    print("\nPermission checks:")
    print(f"  Admin can ingest: {rbac.check_permission('admin1', 'ingest_documents')}")
    print(f"  Operator can ingest: {rbac.check_permission('operator1', 'ingest_documents')}")
    print(f"  Analyst can query: {rbac.check_permission('analyst1', 'query_system')}")
    
    # Test clearance
    print("\nClearance checks:")
    print(f"  Analyst TS can access SECRET: {rbac.check_clearance('analyst1', ClassificationLevel.SECRET)}")
    print(f"  Operator can access SECRET: {rbac.check_clearance('operator1', ClassificationLevel.SECRET)}")
    
    # Audit logging
    print("\nAudit logging:")
    audit_log = Path("logs/example_audit.log")
    audit_log.parent.mkdir(exist_ok=True)
    
    logger = AuditLogger(audit_log, enable_encryption=False)
    logger.log_query(
        user_id="analyst1",
        query="What is the radar range?",
        classification=ClassificationLevel.SECRET,
        retrieved_docs=[],
        success=True
    )
    
    events = logger.read_events()
    print(f"  Logged {len(events)} events")
    print(f"  Last event: {events[-1].event_type.value} by {events[-1].user_id}")


def example_4_network_verification():
    """Example 4: Network isolation verification"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Network Isolation Verification")
    print("=" * 60 + "\n")
    
    from src.security import NetworkIsolationVerifier
    
    results = NetworkIsolationVerifier.verify_all()
    
    print(f"Overall status: {'PASS' if results['all_passed'] else 'FAIL'}")
    print(f"Checks passed: {results['passed_count']}/{results['total_count']}\n")
    
    for check in results['checks']:
        status = "[OK]" if check['passed'] else "[FAIL]"
        print(f"{status} {check['name']}")
        print(f"  {check['details']}")


def example_5_hallucination_detection():
    """Example 5: Hallucination detection"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Hallucination Detection")
    print("=" * 60 + "\n")
    
    from src.llm import SafetyFilter
    
    context = "The AN/SPY-7 radar operates at 2.9-3.1 GHz with a maximum range of 400km."
    
    # Good response (grounded in context)
    good_response = "The AN/SPY-7 operates at S-band frequencies (2.9-3.1 GHz) with a 400km maximum range."
    is_hallucination = SafetyFilter.check_hallucination(good_response, context)
    print(f"Good response hallucination check: {is_hallucination}")
    print(f"  Response: {good_response[:80]}...")
    
    # Bad response (external knowledge)
    bad_response = "Based on my training, radars typically use various frequencies for different purposes."
    is_hallucination = SafetyFilter.check_hallucination(bad_response, context)
    print(f"\nBad response hallucination check: {is_hallucination}")
    print(f"  Response: {bad_response[:80]}...")
    
    # Validate responses
    print("\nValidation with safety filter:")
    is_valid, filtered = SafetyFilter.validate_response(good_response, context, strict=True)
    print(f"  Good response valid: {is_valid}")
    
    is_valid, filtered = SafetyFilter.validate_response(bad_response, context, strict=True)
    print(f"  Bad response valid: {is_valid}")
    if not is_valid:
        print(f"  Filtered to: {filtered}")


def example_6_full_pipeline():
    """Example 6: Full RAG pipeline (without actual LLM)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Full Pipeline Simulation")
    print("=" * 60 + "\n")
    
    from src.ingestion import DocumentLoader, DocumentChunker
    from src.llm import PromptTemplate
    from src.retrieval import format_context, RetrievalResult
    
    # Load documents
    loader = DocumentLoader()
    doc = loader.load(
        Path("data/documents/radar_technical_manual.txt"),
        classification=ClassificationLevel.CONFIDENTIAL
    )
    
    # Chunk
    chunker = DocumentChunker(chunk_size=512, chunk_overlap=50)
    chunks = chunker.chunk_document(doc)
    
    print(f"Processed {len(chunks)} chunks from document")
    
    # Simulate retrieval results
    mock_results = [
        RetrievalResult(
            chunk_id=chunks[0].chunk_id,
            content=chunks[0].content[:200],
            score=0.89,
            metadata=chunks[0].metadata,
            rank=0
        )
    ]
    
    # Format context
    context = format_context(mock_results)
    print(f"\nFormatted context length: {len(context)} characters")
    
    # Generate prompt
    query = "What is the frequency range of the AN/SPY-7 radar?"
    prompt = PromptTemplate.format_rag_prompt(query, context)
    
    print(f"\nQuery: {query}")
    print(f"Prompt length: {len(prompt)} characters")
    print("\nPrompt preview:")
    print(prompt[:400] + "...")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("OFFLINE PRIVATE LLM-RAG SYSTEM")
    print("Example Usage Demonstrations")
    print("=" * 60)
    
    examples = [
        example_1_load_documents,
        example_2_radar_logs,
        example_3_security_features,
        example_4_network_verification,
        example_5_hallucination_detection,
        example_6_full_pipeline
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            logger.error(f"Example failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
