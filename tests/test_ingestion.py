"""
Tests for document ingestion pipeline
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.ingestion import DocumentLoader, DocumentChunker, SemanticChunker
from src.config import ClassificationLevel


class TestDocumentLoader:
    """Test document loading"""
    
    def test_load_text_file(self, tmp_path):
        """Test loading a text file"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is a test document.\nWith multiple lines.")
        
        loader = DocumentLoader()
        doc = loader.load(test_file, classification=ClassificationLevel.UNCLASSIFIED)
        
        assert doc.content == "This is a test document.\nWith multiple lines."
        assert doc.metadata["classification"] == "UNCLASSIFIED"
        assert doc.metadata["document_type"] == "txt"
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error"""
        loader = DocumentLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load(Path("/nonexistent/file.txt"))
    
    def test_document_checksum(self, tmp_path):
        """Test document checksum is computed"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        loader = DocumentLoader()
        doc = loader.load(test_file)
        
        assert "checksum" in doc.metadata
        assert len(doc.metadata["checksum"]) == 64  # SHA256 hex


class TestDocumentChunker:
    """Test document chunking"""
    
    def test_chunk_small_document(self, tmp_path):
        """Test chunking a small document"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Short content")
        
        loader = DocumentLoader()
        doc = loader.load(test_file)
        
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=10)
        chunks = chunker.chunk_document(doc)
        
        assert len(chunks) == 1
        assert chunks[0].content == "Short content"
    
    def test_chunk_large_document(self, tmp_path):
        """Test chunking a large document"""
        # Create document larger than chunk size
        content = " ".join(["This is sentence number {}.".format(i) for i in range(100)])
        
        test_file = tmp_path / "test.txt"
        test_file.write_text(content)
        
        loader = DocumentLoader()
        doc = loader.load(test_file)
        
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        chunks = chunker.chunk_document(doc)
        
        assert len(chunks) > 1
        assert all(chunk.doc_id == doc.doc_id for chunk in chunks)
        assert all(chunk.chunk_index < len(chunks) for chunk in chunks)
    
    def test_chunk_overlap(self, tmp_path):
        """Test that chunks have proper overlap"""
        content = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z"
        
        test_file = tmp_path / "test.txt"
        test_file.write_text(content)
        
        loader = DocumentLoader()
        doc = loader.load(test_file)
        
        chunker = DocumentChunker(chunk_size=10, chunk_overlap=5)
        chunks = chunker.chunk_document(doc)
        
        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            for i in range(len(chunks) - 1):
                chunk1_words = set(chunks[i].content.split())
                chunk2_words = set(chunks[i + 1].content.split())
                
                # Should have some common words (overlap)
                assert len(chunk1_words & chunk2_words) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
