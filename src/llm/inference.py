"""
Offline LLM Inference for Private RAG System
Uses llama.cpp for efficient CPU/GPU inference with quantized models
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import os

# Disable all telemetry
os.environ["LLAMA_CPP_NO_TELEMETRY"] = "1"

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


logger = logging.getLogger(__name__)


class OfflineLLM:
    """
    Offline LLM inference engine
    CRITICAL: No network access, no telemetry
    """
    
    def __init__(self,
                 model_path: Path,
                 n_ctx: int = 4096,
                 n_threads: int = 8,
                 n_gpu_layers: int = 0,
                 temperature: float = 0.1,
                 max_tokens: int = 512,
                 verbose: bool = False):
        """
        Initialize LLM
        
        Args:
            model_path: Path to GGUF model file
            n_ctx: Context length
            n_threads: Number of CPU threads
            n_gpu_layers: Number of layers to offload to GPU (0 = CPU only)
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens to generate
            verbose: Enable verbose logging
        """
        if Llama is None:
            raise ImportError(
                "llama-cpp-python not installed. "
                "Install with: pip install llama-cpp-python"
            )
        
        self.model_path = Path(model_path)
        
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. "
                f"Download model offline first."
            )
        
        logger.info(f"Loading LLM from {self.model_path}")
        logger.info(f"Context length: {n_ctx}, Threads: {n_threads}, GPU layers: {n_gpu_layers}")
        
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        try:
            self.model = Llama(
                model_path=str(self.model_path),
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                verbose=verbose
            )
            
            logger.info("LLM loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            raise
    
    def generate(self,
                prompt: str,
                temperature: Optional[float] = None,
                max_tokens: Optional[int] = None,
                stop: Optional[list] = None,
                **kwargs) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences
            **kwargs: Additional generation parameters
        
        Returns:
            Generated text
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        logger.info(f"Generating with temperature={temp}, max_tokens={max_tok}")
        
        try:
            response = self.model(
                prompt,
                temperature=temp,
                max_tokens=max_tok,
                stop=stop or [],
                echo=False,
                **kwargs
            )
            
            generated_text = response["choices"][0]["text"]
            
            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text.strip()
        
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def chat(self,
            messages: list,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            **kwargs) -> str:
        """
        Generate response using chat format
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Additional generation parameters
        
        Returns:
            Generated response
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        try:
            response = self.model.create_chat_completion(
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                **kwargs
            )
            
            generated_text = response["choices"][0]["message"]["content"]
            
            logger.info(f"Chat response generated: {len(generated_text)} characters")
            return generated_text.strip()
        
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_path": str(self.model_path),
            "n_ctx": self.model.n_ctx(),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }


class PromptTemplate:
    """
    Prompt templates for RAG system
    Enforces strict context-only responses
    """
    
    SYSTEM_PROMPT = """You are a secure AI assistant operating in an air-gapped defense system.

CRITICAL RULES:
1. Answer ONLY using information from the provided CONTEXT below
2. If the answer is not in the CONTEXT, respond EXACTLY: "Insufficient information in provided documents"
3. NEVER use external knowledge or training data beyond the CONTEXT
4. Always cite source documents using [Source: filename]
5. If classification levels conflict, defer to highest classification
6. Be precise and factual
7. Do not speculate or make assumptions"""
    
    RAG_TEMPLATE = """SYSTEM:
{system_prompt}

CONTEXT:
{context}

USER QUERY:
{query}

ASSISTANT:"""
    
    CLASSIFICATION_WARNING = """
WARNING: This response contains information classified as {classification}.
Handle accordingly and ensure proper clearance."""
    
    @staticmethod
    def format_rag_prompt(query: str, context: str, system_prompt: Optional[str] = None) -> str:
        """
        Format RAG prompt
        
        Args:
            query: User query
            context: Retrieved context
            system_prompt: Optional custom system prompt
        
        Returns:
            Formatted prompt
        """
        sys_prompt = system_prompt or PromptTemplate.SYSTEM_PROMPT
        
        return PromptTemplate.RAG_TEMPLATE.format(
            system_prompt=sys_prompt,
            context=context,
            query=query
        )
    
    @staticmethod
    def format_chat_messages(query: str, context: str,
                            system_prompt: Optional[str] = None) -> list:
        """
        Format as chat messages
        
        Args:
            query: User query
            context: Retrieved context
            system_prompt: Optional custom system prompt
        
        Returns:
            List of message dicts
        """
        sys_prompt = system_prompt or PromptTemplate.SYSTEM_PROMPT
        
        user_message = f"""CONTEXT:
{context}

USER QUERY:
{query}"""
        
        return [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_message}
        ]


class SafetyFilter:
    """
    Filter LLM responses for safety and compliance
    """
    
    HALLUCINATION_PHRASES = [
        "based on my knowledge",
        "as far as i know",
        "generally speaking",
        "in general",
        "from my understanding",
        "from my training"
    ]
    
    INSUFFICIENT_INFO_RESPONSE = "Insufficient information in provided documents"
    
    @staticmethod
    def check_hallucination(response: str, context: str) -> bool:
        """
        Check if response may contain hallucination
        
        Args:
            response: LLM response
            context: Provided context
        
        Returns:
            True if potential hallucination detected
        """
        response_lower = response.lower()
        
        # Check for hallucination phrases
        for phrase in SafetyFilter.HALLUCINATION_PHRASES:
            if phrase in response_lower:
                logger.warning(f"Potential hallucination detected: '{phrase}'")
                return True
        
        # Check if response contains information not in context
        # (Simple heuristic - can be enhanced)
        response_words = set(response_lower.split())
        context_words = set(context.lower().split())
        
        # Calculate overlap
        overlap = len(response_words & context_words) / len(response_words) if response_words else 0
        
        if overlap < 0.3:  # Less than 30% overlap
            logger.warning(f"Low context overlap: {overlap:.2%}")
            return True
        
        return False
    
    @staticmethod
    def validate_response(response: str, context: str, strict: bool = True) -> tuple:
        """
        Validate LLM response
        
        Args:
            response: LLM response
            context: Provided context
            strict: Enable strict validation
        
        Returns:
            (is_valid, filtered_response)
        """
        # Check for insufficient information response
        if SafetyFilter.INSUFFICIENT_INFO_RESPONSE.lower() in response.lower():
            return True, response
        
        # Check for hallucination
        if strict and SafetyFilter.check_hallucination(response, context):
            filtered = SafetyFilter.INSUFFICIENT_INFO_RESPONSE
            return False, filtered
        
        return True, response
