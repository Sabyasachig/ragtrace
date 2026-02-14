"""
Cost calculation module for RAG Debugger.

This module provides accurate token counting and cost estimation
for various LLM models and embedding models.

Uses tiktoken for accurate OpenAI token counting.
"""

import tiktoken
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


# Pricing per 1K tokens (as of 2024)
# Source: https://openai.com/pricing
PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4": {
        "input": 0.03,  # $0.03 per 1K input tokens
        "output": 0.06,  # $0.06 per 1K output tokens
    },
    "gpt-4-turbo-preview": {
        "input": 0.01,
        "output": 0.03,
    },
    "gpt-4-32k": {
        "input": 0.06,
        "output": 0.12,
    },
    "gpt-3.5-turbo": {
        "input": 0.0015,  # $0.0015 per 1K input tokens
        "output": 0.002,  # $0.002 per 1K output tokens
    },
    "gpt-3.5-turbo-16k": {
        "input": 0.003,
        "output": 0.004,
    },
    "text-embedding-ada-002": {
        "input": 0.0001,  # $0.0001 per 1K tokens
    },
    "text-embedding-3-small": {
        "input": 0.00002,
    },
    "text-embedding-3-large": {
        "input": 0.00013,
    },
}

# Default pricing for unknown models (use GPT-3.5 as baseline)
DEFAULT_PRICING = {
    "input": 0.0015,
    "output": 0.002,
}


class CostCalculator:
    """
    Calculates costs for LLM operations.
    
    Provides methods to:
    - Count tokens accurately using tiktoken
    - Calculate embedding costs
    - Calculate generation costs (input + output)
    - Estimate total pipeline costs
    """
    
    def __init__(self):
        """Initialize cost calculator with tokenizer cache."""
        self._tokenizer_cache: Dict[str, tiktoken.Encoding] = {}
    
    def get_tokenizer(self, model: str) -> tiktoken.Encoding:
        """
        Get tiktoken encoder for a model.
        
        Args:
            model: Model name (e.g., "gpt-4")
            
        Returns:
            tiktoken.Encoding instance
        """
        if model not in self._tokenizer_cache:
            try:
                # Try to get encoding for specific model
                self._tokenizer_cache[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fall back to cl100k_base (used by GPT-4, GPT-3.5)
                logger.warning(f"No specific encoding for {model}, using cl100k_base")
                self._tokenizer_cache[model] = tiktoken.get_encoding("cl100k_base")
        
        return self._tokenizer_cache[model]
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens for
            model: Model name (for tokenizer selection)
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        
        try:
            encoding = self.get_tokenizer(model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters for English)
            return len(text) // 4
    
    def calculate_embedding_cost(
        self,
        num_tokens: int,
        model: str = "text-embedding-ada-002"
    ) -> float:
        """
        Calculate cost for embedding operations.
        
        Args:
            num_tokens: Number of tokens in the text to embed
            model: Embedding model name
            
        Returns:
            Cost in USD
        """
        pricing = PRICING.get(model, {"input": 0.0001})
        cost_per_1k = pricing["input"]
        return (num_tokens / 1000) * cost_per_1k
    
    def calculate_generation_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-3.5-turbo"
    ) -> tuple[float, float, float]:
        """
        Calculate cost for LLM generation.
        
        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
            model: LLM model name
            
        Returns:
            Tuple of (input_cost, output_cost, total_cost) in USD
        """
        pricing = PRICING.get(model, DEFAULT_PRICING)
        
        input_cost_per_1k = pricing["input"]
        output_cost_per_1k = pricing.get("output", pricing["input"])  # Some models only have input pricing
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        return input_cost, output_cost, total_cost
    
    def estimate_prompt_tokens(
        self,
        query: str,
        chunks: list[str],
        template: Optional[str] = None,
        model: str = "gpt-3.5-turbo"
    ) -> int:
        """
        Estimate tokens in assembled prompt.
        
        Args:
            query: User query
            chunks: Retrieved chunks to include
            template: Optional prompt template
            model: Model for tokenizer
            
        Returns:
            Estimated token count
        """
        # Build a rough approximation of the final prompt
        if template:
            # Use provided template
            combined_chunks = "\n\n".join(chunks)
            prompt_text = template.format(context=combined_chunks, query=query)
        else:
            # Use default RAG template
            combined_chunks = "\n\n".join(chunks)
            prompt_text = f"Context:\n{combined_chunks}\n\nQuestion: {query}\n\nAnswer:"
        
        return self.count_tokens(prompt_text, model)
    
    def get_pricing_info(self, model: str) -> Dict[str, float]:
        """
        Get pricing information for a model.
        
        Args:
            model: Model name
            
        Returns:
            Dictionary with input/output pricing per 1K tokens
        """
        return PRICING.get(model, DEFAULT_PRICING).copy()
    
    def format_cost(self, cost: float) -> str:
        """
        Format cost for display.
        
        Args:
            cost: Cost in USD
            
        Returns:
            Formatted string (e.g., "$0.027")
        """
        if cost < 0.0001:
            return f"${cost:.6f}"
        elif cost < 0.01:
            return f"${cost:.5f}"
        else:
            return f"${cost:.3f}"


# Global calculator instance
_calculator: Optional[CostCalculator] = None


def get_calculator() -> CostCalculator:
    """
    Get global cost calculator instance.
    
    Returns:
        CostCalculator instance
    """
    global _calculator
    if _calculator is None:
        _calculator = CostCalculator()
    return _calculator


# Convenience functions

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens in text."""
    return get_calculator().count_tokens(text, model)


def calculate_embedding_cost(num_tokens: int, model: str = "text-embedding-ada-002") -> float:
    """Calculate embedding cost."""
    return get_calculator().calculate_embedding_cost(num_tokens, model)


def calculate_generation_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-3.5-turbo"
) -> tuple[float, float, float]:
    """Calculate generation cost."""
    return get_calculator().calculate_generation_cost(input_tokens, output_tokens, model)


def format_cost(cost: float) -> str:
    """Format cost for display."""
    return get_calculator().format_cost(cost)
