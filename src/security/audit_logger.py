"""
Security and Audit Logging for Offline Private LLM-RAG System
Provides encrypted audit trails and access control
"""

import logging
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from ..config import ClassificationLevel


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of auditable events"""
    QUERY = "query"
    DOCUMENT_INGEST = "document_ingest"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    AUTHENTICATION = "authentication"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ERROR = "error"


@dataclass
class AuditEvent:
    """Represents an audit event"""
    timestamp: str
    event_type: EventType
    user_id: str
    classification: ClassificationLevel
    details: Dict[str, Any]
    query_hash: Optional[str] = None
    success: bool = True


class AuditLogger:
    """
    Encrypted audit logger
    Logs all security-relevant events
    """
    
    def __init__(self, log_path: Path, enable_encryption: bool = True,
                 encryption_key: Optional[bytes] = None):
        """
        Initialize audit logger
        
        Args:
            log_path: Path to audit log file
            enable_encryption: Enable log encryption
            encryption_key: Encryption key for logs
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.enable_encryption = enable_encryption
        
        if enable_encryption:
            if encryption_key is None:
                import secrets
                encryption_key = secrets.token_bytes(32)
                logger.warning("Generated new encryption key for audit logs")
            
            self.encryption_key = encryption_key
        
        logger.info(f"Audit logger initialized: {self.log_path}")
    
    def log_event(self, event: AuditEvent):
        """
        Log an audit event
        
        Args:
            event: AuditEvent to log
        """
        # Serialize event
        event_dict = asdict(event)
        event_dict["event_type"] = event.event_type.value
        event_dict["classification"] = event.classification.name
        
        log_line = json.dumps(event_dict)
        
        # Encrypt if enabled
        if self.enable_encryption:
            log_line = self._encrypt_log_line(log_line)
        
        # Write to file
        with open(self.log_path, 'a') as f:
            f.write(log_line + "\n")
    
    def log_query(self, user_id: str, query: str, classification: ClassificationLevel,
                 retrieved_docs: list, success: bool = True):
        """Log a query event"""
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=EventType.QUERY,
            user_id=user_id,
            classification=classification,
            query_hash=query_hash,
            details={
                "query_length": len(query),
                "retrieved_count": len(retrieved_docs),
                "doc_ids": [doc.get("chunk_id") if isinstance(doc, dict) else doc.chunk_id for doc in retrieved_docs[:5]]
            },
            success=success
        )
        
        self.log_event(event)
        logger.info(f"Logged query event: user={user_id}, classification={classification.name}")
    
    def log_document_ingest(self, user_id: str, doc_id: str,
                           classification: ClassificationLevel, success: bool = True):
        """Log document ingestion"""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=EventType.DOCUMENT_INGEST,
            user_id=user_id,
            classification=classification,
            details={"doc_id": doc_id},
            success=success
        )
        
        self.log_event(event)
    
    def log_access_denied(self, user_id: str, required_classification: ClassificationLevel,
                         user_classification: ClassificationLevel):
        """Log access denial"""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=EventType.ACCESS_DENIED,
            user_id=user_id,
            classification=required_classification,
            details={
                "required": required_classification.name,
                "user_clearance": user_classification.name
            },
            success=False
        )
        
        self.log_event(event)
        logger.warning(f"Access denied: user={user_id}, required={required_classification.name}")
    
    def log_authentication(self, user_id: str, success: bool):
        """Log authentication attempt"""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=EventType.AUTHENTICATION,
            user_id=user_id,
            classification=ClassificationLevel.UNCLASSIFIED,
            details={"method": "local"},
            success=success
        )
        
        self.log_event(event)
    
    def _encrypt_log_line(self, log_line: str) -> str:
        """Encrypt a log line"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        import os
        
        aesgcm = AESGCM(self.encryption_key)
        nonce = os.urandom(12)
        
        ciphertext = aesgcm.encrypt(nonce, log_line.encode(), None)
        encrypted = base64.b64encode(nonce + ciphertext).decode()
        
        return encrypted
    
    def _decrypt_log_line(self, encrypted_line: str) -> str:
        """Decrypt a log line"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        
        encrypted_data = base64.b64decode(encrypted_line)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        aesgcm = AESGCM(self.encryption_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode()
    
    def read_events(self, limit: Optional[int] = None) -> list:
        """
        Read audit events (requires decryption key)
        
        Args:
            limit: Maximum number of events to read
        
        Returns:
            List of AuditEvent objects
        """
        if not self.log_path.exists():
            return []
        
        events = []
        with open(self.log_path, 'r') as f:
            lines = f.readlines()
            if limit:
                lines = lines[-limit:]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    if self.enable_encryption:
                        line = self._decrypt_log_line(line)
                    
                    event_dict = json.loads(line)
                    # Reconstruct enums
                    event_dict["event_type"] = EventType(event_dict["event_type"])
                    event_dict["classification"] = ClassificationLevel[event_dict["classification"]]
                    
                    events.append(AuditEvent(**event_dict))
                
                except Exception as e:
                    logger.error(f"Failed to parse audit log line: {e}")
        
        return events


@dataclass
class User:
    """Represents a system user"""
    user_id: str
    clearance: ClassificationLevel
    roles: list
    active: bool = True


class RBACManager:
    """
    Role-Based Access Control Manager
    """
    
    ROLES = {
        "ADMIN": ["ingest_documents", "query_system", "view_logs", "manage_users", "configure_system"],
        "ANALYST_TS": ["query_system", "view_logs"],
        "ANALYST_S": ["query_system"],
        "ANALYST_C": ["query_system"],
        "OPERATOR": ["query_system"]
    }
    
    ROLE_CLEARANCES = {
        "ADMIN": ClassificationLevel.TOP_SECRET,
        "ANALYST_TS": ClassificationLevel.TOP_SECRET,
        "ANALYST_S": ClassificationLevel.SECRET,
        "ANALYST_C": ClassificationLevel.CONFIDENTIAL,
        "OPERATOR": ClassificationLevel.UNCLASSIFIED
    }
    
    def __init__(self):
        self.users: Dict[str, User] = {}
    
    def add_user(self, user_id: str, roles: list, clearance: Optional[ClassificationLevel] = None):
        """
        Add a user
        
        Args:
            user_id: User identifier
            roles: List of role names
            clearance: Optional clearance override
        """
        # Determine clearance from highest role
        if clearance is None:
            clearance = max([self.ROLE_CLEARANCES.get(role, ClassificationLevel.UNCLASSIFIED)
                           for role in roles])
        
        user = User(
            user_id=user_id,
            clearance=clearance,
            roles=roles,
            active=True
        )
        
        self.users[user_id] = user
        logger.info(f"Added user: {user_id}, roles={roles}, clearance={clearance.name}")
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if user has permission
        
        Args:
            user_id: User identifier
            permission: Permission name
        
        Returns:
            True if user has permission
        """
        user = self.users.get(user_id)
        if not user or not user.active:
            return False
        
        for role in user.roles:
            role_permissions = self.ROLES.get(role, [])
            if permission in role_permissions:
                return True
        
        return False
    
    def check_clearance(self, user_id: str, required_clearance: ClassificationLevel) -> bool:
        """
        Check if user has sufficient clearance
        
        Args:
            user_id: User identifier
            required_clearance: Required classification level
        
        Returns:
            True if user has sufficient clearance
        """
        user = self.users.get(user_id)
        if not user or not user.active:
            return False
        
        return user.clearance >= required_clearance
    
    def get_user_clearance(self, user_id: str) -> Optional[ClassificationLevel]:
        """Get user's clearance level"""
        user = self.users.get(user_id)
        return user.clearance if user else None
