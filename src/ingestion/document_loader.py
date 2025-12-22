"""
Document Loader for Offline Private LLM-RAG System
Supports PDFs, text files, radar logs, and structured data
"""

import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

# Document processing imports
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from ..config import ClassificationLevel


logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a loaded document"""
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate and enhance metadata"""
        required_fields = ["source_file", "classification", "document_type"]
        for field in required_fields:
            if field not in self.metadata:
                raise ValueError(f"Missing required metadata field: {field}")
        
        # Add checksum if not present
        if "checksum" not in self.metadata:
            self.metadata["checksum"] = self._compute_checksum()
        
        # Add ingest timestamp
        if "ingest_date" not in self.metadata:
            self.metadata["ingest_date"] = datetime.utcnow().isoformat()
    
    def _compute_checksum(self) -> str:
        """Compute SHA256 checksum of content"""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()


class DocumentLoader:
    """Load documents from various formats"""
    
    def __init__(self, default_classification: ClassificationLevel = ClassificationLevel.UNCLASSIFIED):
        self.default_classification = default_classification
        self.supported_extensions = {
            '.pdf': self._load_pdf,
            '.txt': self._load_text,
            '.md': self._load_text,
            '.log': self._load_text,
            '.csv': self._load_csv,
            '.json': self._load_json,
        }
    
    def load(self, file_path: Path, classification: Optional[ClassificationLevel] = None,
             metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        Load a document from file
        
        Args:
            file_path: Path to document
            classification: Security classification level
            metadata: Additional metadata
        
        Returns:
            Document object
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        extension = file_path.suffix.lower()
        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {extension}")
        
        logger.info(f"Loading document: {file_path}")
        
        # Load content using appropriate loader
        content = self.supported_extensions[extension](file_path)
        
        # Build metadata
        doc_metadata = {
            "source_file": str(file_path.absolute()),
            "classification": (classification or self.default_classification).name,
            "document_type": extension[1:],  # Remove leading dot
            "file_size": file_path.stat().st_size,
            "file_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }
        
        # Merge user-provided metadata
        if metadata:
            doc_metadata.update(metadata)
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        return Document(
            doc_id=doc_id,
            content=content,
            metadata=doc_metadata
        )
    
    def _load_pdf(self, file_path: Path) -> str:
        """Load PDF document"""
        if pdfplumber is None:
            raise ImportError("pdfplumber not installed. Install with: pip install pdfplumber")
        
        content_parts = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        content_parts.append(f"[Page {page_num}]\n{text}")
            
            return "\n\n".join(content_parts)
        
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {e}")
            raise
    
    def _load_text(self, file_path: Path) -> str:
        """Load plain text document"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading text file {file_path}: {e}")
            raise
    
    def _load_csv(self, file_path: Path) -> str:
        """Load CSV as formatted text"""
        import csv
        
        content_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=1):
                    row_text = " | ".join([f"{k}: {v}" for k, v in row.items()])
                    content_parts.append(f"Row {row_num}: {row_text}")
            
            return "\n".join(content_parts)
        
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            raise
    
    def _load_json(self, file_path: Path) -> str:
        """Load JSON as formatted text"""
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to readable text format
            return json.dumps(data, indent=2)
        
        except Exception as e:
            logger.error(f"Error loading JSON {file_path}: {e}")
            raise
    
    def load_directory(self, directory: Path, recursive: bool = True,
                      classification: Optional[ClassificationLevel] = None) -> List[Document]:
        """
        Load all supported documents from a directory
        
        Args:
            directory: Directory path
            recursive: Search subdirectories
            classification: Default classification for all documents
        
        Returns:
            List of Document objects
        """
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")
        
        documents = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                try:
                    doc = self.load(file_path, classification=classification)
                    documents.append(doc)
                except Exception as e:
                    logger.error(f"Failed to load {file_path}: {e}")
        
        logger.info(f"Loaded {len(documents)} documents from {directory}")
        return documents


class RadarLogLoader(DocumentLoader):
    """Specialized loader for radar log files"""
    
    def __init__(self, default_classification: ClassificationLevel = ClassificationLevel.SECRET):
        super().__init__(default_classification=default_classification)
        self.supported_extensions['.dat'] = self._load_radar_log
    
    def _load_radar_log(self, file_path: Path) -> str:
        """
        Parse radar log files
        Expected format: Timestamp, Azimuth, Range, Velocity, Signal_Strength
        """
        content_parts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse radar data
                    parts = line.split(',')
                    if len(parts) >= 5:
                        timestamp, azimuth, range_val, velocity, signal = parts[:5]
                        formatted = (
                            f"Track {line_num}: "
                            f"Time={timestamp.strip()}, "
                            f"Azimuth={azimuth.strip()}°, "
                            f"Range={range_val.strip()}km, "
                            f"Velocity={velocity.strip()}m/s, "
                            f"Signal={signal.strip()}dB"
                        )
                        content_parts.append(formatted)
            
            return "\n".join(content_parts)
        
        except Exception as e:
            logger.error(f"Error loading radar log {file_path}: {e}")
            raise
