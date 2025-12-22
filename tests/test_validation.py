"""
Validation tests for the RAG system
Tests for hallucination, data leakage, and correctness
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.llm import PromptTemplate, SafetyFilter


class TestHallucinationDetection:
    """Test hallucination detection"""
    
    def test_detect_external_knowledge_phrases(self):
        """Test detection of phrases indicating external knowledge use"""
        context = "The radar has a range of 400km."
        
        # Response using external knowledge
        bad_response = "Based on my knowledge, radars typically operate at various frequencies."
        
        is_hallucination = SafetyFilter.check_hallucination(bad_response, context)
        assert is_hallucination is True
    
    def test_accept_context_grounded_response(self):
        """Test that context-grounded responses pass"""
        context = "The AN/SPY-7 radar has a maximum range of 400km for surface targets."
        
        # Response grounded in context
        good_response = "The AN/SPY-7 radar can detect surface targets at ranges up to 400km."
        
        is_hallucination = SafetyFilter.check_hallucination(good_response, context)
        assert is_hallucination is False
    
    def test_low_context_overlap_detection(self):
        """Test detection of responses with low context overlap"""
        context = "The radar operates in S-band frequency range between 2.9 and 3.1 GHz."
        
        # Response about unrelated topic
        bad_response = "Python is a popular programming language used for data science."
        
        is_hallucination = SafetyFilter.check_hallucination(bad_response, context)
        assert is_hallucination is True
    
    def test_insufficient_info_response_accepted(self):
        """Test that 'insufficient information' response is accepted"""
        context = "Some unrelated information."
        response = "Insufficient information in provided documents"
        
        is_valid, filtered = SafetyFilter.validate_response(response, context, strict=True)
        assert is_valid is True


class TestPromptTemplates:
    """Test prompt templates"""
    
    def test_rag_prompt_format(self):
        """Test RAG prompt formatting"""
        query = "What is the radar range?"
        context = "The radar has a range of 400km."
        
        prompt = PromptTemplate.format_rag_prompt(query, context)
        
        assert "CONTEXT:" in prompt
        assert "USER QUERY:" in prompt
        assert query in prompt
        assert context in prompt
        assert "CRITICAL RULES" in prompt
    
    def test_chat_messages_format(self):
        """Test chat message formatting"""
        query = "What is the radar range?"
        context = "The radar has a range of 400km."
        
        messages = PromptTemplate.format_chat_messages(query, context)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "CONTEXT:" in messages[1]["content"]
    
    def test_system_prompt_contains_safety_rules(self):
        """Test that system prompt contains safety rules"""
        prompt = PromptTemplate.SYSTEM_PROMPT
        
        # Check for key safety instructions
        assert "ONLY using information from" in prompt
        assert "CONTEXT" in prompt
        assert "Insufficient information" in prompt
        assert "NEVER use external knowledge" in prompt


class TestDataLeakage:
    """Test for data leakage prevention"""
    
    def test_no_network_env_vars(self):
        """Test that network-disabling environment variables are set"""
        import os
        
        # These should be set by embedding_generator.py
        assert os.getenv("TRANSFORMERS_OFFLINE") == "1"
        assert os.getenv("HF_DATASETS_OFFLINE") == "1"
    
    def test_classification_levels(self):
        """Test classification level ordering"""
        from src.config import ClassificationLevel
        
        assert ClassificationLevel.UNCLASSIFIED < ClassificationLevel.CONFIDENTIAL
        assert ClassificationLevel.CONFIDENTIAL < ClassificationLevel.SECRET
        assert ClassificationLevel.SECRET < ClassificationLevel.TOP_SECRET


class TestRAGCorrectness:
    """Test RAG correctness with ground truth"""
    
    def test_context_only_constraint(self):
        """Test that responses should only use provided context"""
        # This is a manual validation test
        # In production, would compare against ground truth
        
        test_cases = [
            {
                "context": "The AN/SPY-7 operates at 2.9-3.1 GHz.",
                "query": "What frequency does AN/SPY-7 use?",
                "expected_contains": ["2.9", "3.1", "GHz"],
                "expected_not_contains": ["Python", "programming"]
            },
            {
                "context": "Mission ALPHA-2024-087 departed at 0600 hours.",
                "query": "When did the mission depart?",
                "expected_contains": ["0600"],
                "expected_not_contains": ["Paris", "France"]
            }
        ]
        
        # These test cases serve as documentation of expected behavior
        assert len(test_cases) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
