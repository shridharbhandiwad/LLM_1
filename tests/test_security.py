"""
Tests for security components
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.security import AuditLogger, RBACManager, EventType
from src.config import ClassificationLevel


class TestAuditLogger:
    """Test audit logging"""
    
    def test_log_query_event(self, tmp_path):
        """Test logging a query event"""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path, enable_encryption=False)
        
        logger.log_query(
            user_id="test_user",
            query="test query",
            classification=ClassificationLevel.UNCLASSIFIED,
            retrieved_docs=[],
            success=True
        )
        
        # Read back events
        events = logger.read_events()
        assert len(events) == 1
        assert events[0].user_id == "test_user"
        assert events[0].event_type == EventType.QUERY
    
    def test_encrypted_logging(self, tmp_path):
        """Test encrypted audit logging"""
        log_path = tmp_path / "audit_encrypted.log"
        encryption_key = b"0" * 32  # 32-byte key
        
        logger = AuditLogger(log_path, enable_encryption=True, encryption_key=encryption_key)
        
        logger.log_query(
            user_id="test_user",
            query="sensitive query",
            classification=ClassificationLevel.SECRET,
            retrieved_docs=[],
            success=True
        )
        
        # Read back with correct key
        events = logger.read_events()
        assert len(events) == 1
        assert events[0].classification == ClassificationLevel.SECRET
    
    def test_access_denied_logging(self, tmp_path):
        """Test logging access denial"""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path, enable_encryption=False)
        
        logger.log_access_denied(
            user_id="low_clearance_user",
            required_classification=ClassificationLevel.TOP_SECRET,
            user_classification=ClassificationLevel.CONFIDENTIAL
        )
        
        events = logger.read_events()
        assert len(events) == 1
        assert events[0].event_type == EventType.ACCESS_DENIED
        assert events[0].success is False


class TestRBACManager:
    """Test role-based access control"""
    
    def test_add_user(self):
        """Test adding a user"""
        rbac = RBACManager()
        rbac.add_user("analyst1", roles=["ANALYST_S"])
        
        assert "analyst1" in rbac.users
        assert rbac.users["analyst1"].clearance == ClassificationLevel.SECRET
    
    def test_check_permission(self):
        """Test permission checking"""
        rbac = RBACManager()
        rbac.add_user("admin1", roles=["ADMIN"])
        rbac.add_user("operator1", roles=["OPERATOR"])
        
        # Admin should have all permissions
        assert rbac.check_permission("admin1", "ingest_documents")
        assert rbac.check_permission("admin1", "query_system")
        
        # Operator should only query
        assert rbac.check_permission("operator1", "query_system")
        assert not rbac.check_permission("operator1", "ingest_documents")
    
    def test_check_clearance(self):
        """Test clearance checking"""
        rbac = RBACManager()
        rbac.add_user("ts_analyst", roles=["ANALYST_TS"])
        rbac.add_user("c_analyst", roles=["ANALYST_C"])
        
        # TS analyst can access SECRET
        assert rbac.check_clearance("ts_analyst", ClassificationLevel.SECRET)
        assert rbac.check_clearance("ts_analyst", ClassificationLevel.TOP_SECRET)
        
        # C analyst cannot access SECRET
        assert rbac.check_clearance("c_analyst", ClassificationLevel.CONFIDENTIAL)
        assert not rbac.check_clearance("c_analyst", ClassificationLevel.SECRET)
    
    def test_inactive_user(self):
        """Test that inactive users have no permissions"""
        rbac = RBACManager()
        rbac.add_user("user1", roles=["ADMIN"])
        
        # Deactivate user
        rbac.users["user1"].active = False
        
        assert not rbac.check_permission("user1", "query_system")
        assert not rbac.check_clearance("user1", ClassificationLevel.UNCLASSIFIED)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
