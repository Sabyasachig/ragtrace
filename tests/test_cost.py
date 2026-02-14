"""
Unit tests for cost calculation module.

Tests token counting and cost estimation for various models.
"""

import pytest
from core.cost import (
    count_tokens,
    calculate_embedding_cost,
    calculate_generation_cost,
    get_calculator,
    PRICING,
)


class TestTokenCounting:
    """Test token counting functionality."""
    
    def test_count_tokens_simple(self):
        """Test basic token counting."""
        text = "Hello, world!"
        tokens = count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_count_tokens_empty(self):
        """Test token counting with empty string."""
        tokens = count_tokens("")
        assert tokens == 0
    
    def test_count_tokens_long_text(self):
        """Test token counting with longer text."""
        text = "This is a longer piece of text that should have more tokens. " * 10
        tokens = count_tokens(text)
        assert tokens > 50  # Should have many tokens
    
    def test_count_tokens_with_model(self):
        """Test token counting with specific model."""
        text = "Hello, world!"
        tokens_gpt4 = count_tokens(text, model="gpt-4")
        tokens_gpt35 = count_tokens(text, model="gpt-3.5-turbo")
        # Both should give valid counts
        assert tokens_gpt4 > 0
        assert tokens_gpt35 > 0
    
    def test_count_tokens_special_chars(self):
        """Test token counting with special characters."""
        text = "Special chars: @#$%^&*(){}[]|\\:;\"'<>,.?/~`"
        tokens = count_tokens(text)
        assert tokens > 0


class TestEmbeddingCost:
    """Test embedding cost calculation."""
    
    def test_calculate_embedding_cost_ada(self):
        """Test cost calculation for Ada-002 embeddings."""
        text = "This is a test document for embedding."
        tokens = count_tokens(text)
        cost = calculate_embedding_cost(tokens, model="text-embedding-ada-002")
        assert cost > 0
        assert isinstance(cost, float)
        # Cost should be very small for short text
        assert cost < 0.001
    
    def test_calculate_embedding_cost_3_small(self):
        """Test cost calculation for text-embedding-3-small."""
        text = "This is a test document."
        tokens = count_tokens(text)
        cost = calculate_embedding_cost(tokens, model="text-embedding-3-small")
        assert cost > 0
        # Should be cheaper than ada-002
        cost_ada = calculate_embedding_cost(tokens, model="text-embedding-ada-002")
        assert cost < cost_ada
    
    def test_calculate_embedding_cost_default(self):
        """Test cost calculation with default model."""
        text = "Test document"
        tokens = count_tokens(text)
        cost = calculate_embedding_cost(tokens)
        assert cost > 0
    
    def test_calculate_embedding_cost_unknown_model(self):
        """Test cost calculation with unknown model (fallback)."""
        text = "Test document"
        tokens = count_tokens(text)
        cost = calculate_embedding_cost(tokens, model="unknown-embedding-model")
        assert cost > 0  # Should use default pricing


class TestGenerationCost:
    """Test generation cost calculation."""
    
    def test_calculate_generation_cost_gpt4(self):
        """Test cost calculation for GPT-4."""
        prompt = "What is RAG?"
        response = "RAG stands for Retrieval-Augmented Generation."
        input_tokens = count_tokens(prompt, "gpt-4")
        output_tokens = count_tokens(response, "gpt-4")
        input_cost, output_cost, total_cost = calculate_generation_cost(input_tokens, output_tokens, model="gpt-4")
        assert total_cost > 0
        assert isinstance(total_cost, float)
    
    def test_calculate_generation_cost_gpt35(self):
        """Test cost calculation for GPT-3.5."""
        prompt = "What is RAG?"
        response = "RAG stands for Retrieval-Augmented Generation."
        input_tokens = count_tokens(prompt)
        output_tokens = count_tokens(response)
        _, _, cost_gpt4 = calculate_generation_cost(input_tokens, output_tokens, model="gpt-4")
        _, _, cost_gpt35 = calculate_generation_cost(input_tokens, output_tokens, model="gpt-3.5-turbo")
        # GPT-4 should be more expensive than GPT-3.5
        assert cost_gpt4 > cost_gpt35
    
    def test_calculate_generation_cost_empty_response(self):
        """Test cost calculation with empty response."""
        prompt = "Tell me something"
        input_tokens = count_tokens(prompt)
        _, _, total_cost = calculate_generation_cost(input_tokens, 0)
        assert total_cost > 0  # Should still have input cost
    
    def test_calculate_generation_cost_empty_prompt(self):
        """Test cost calculation with empty prompt."""
        response = "Here is a response"
        output_tokens = count_tokens(response)
        _, _, total_cost = calculate_generation_cost(0, output_tokens)
        assert total_cost > 0  # Should still have output cost
    
    def test_calculate_generation_cost_both_empty(self):
        """Test cost calculation with both empty."""
        _, _, total_cost = calculate_generation_cost(0, 0)
        assert total_cost == 0
    
    def test_calculate_generation_cost_long_text(self):
        """Test cost calculation with longer texts."""
        prompt = "Explain RAG in detail." * 100
        response = "RAG is a powerful technique." * 100
        input_tokens = count_tokens(prompt, "gpt-4")
        output_tokens = count_tokens(response, "gpt-4")
        _, _, total_cost = calculate_generation_cost(input_tokens, output_tokens, model="gpt-4")
        # Cost should be proportional to length
        assert total_cost > 0.01  # Should have meaningful cost


class TestModelPricing:
    """Test model pricing utilities."""
    
    def test_get_model_pricing_gpt4(self):
        """Test getting pricing for GPT-4."""
        calc = get_calculator()
        pricing = calc.get_pricing_info("gpt-4")
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] == PRICING["gpt-4"]["input"]
    
    def test_get_model_pricing_partial_match(self):
        """Test partial model name matching."""
        # Should match gpt-4 family
        calc = get_calculator()
        pricing = calc.get_pricing_info("gpt-4-0613")
        assert "input" in pricing
        assert "output" in pricing
    
    def test_get_model_pricing_embedding(self):
        """Test getting pricing for embedding models."""
        calc = get_calculator()
        pricing = calc.get_pricing_info("text-embedding-ada-002")
        assert "input" in pricing
        assert pricing["input"] == PRICING["text-embedding-ada-002"]["input"]
    
    def test_get_model_pricing_unknown(self):
        """Test getting pricing for unknown model."""
        calc = get_calculator()
        pricing = calc.get_pricing_info("unknown-model")
        assert "input" in pricing
        assert "output" in pricing
        # Should use default pricing


class TestPricingTable:
    """Test pricing table structure."""
    
    def test_pricing_table_has_gpt4(self):
        """Test that pricing table includes GPT-4."""
        assert "gpt-4" in PRICING
        assert "input" in PRICING["gpt-4"]
        assert "output" in PRICING["gpt-4"]
    
    def test_pricing_table_has_gpt35(self):
        """Test that pricing table includes GPT-3.5."""
        assert "gpt-3.5-turbo" in PRICING
        assert "input" in PRICING["gpt-3.5-turbo"]
        assert "output" in PRICING["gpt-3.5-turbo"]
    
    def test_pricing_table_has_embeddings(self):
        """Test that pricing table includes embedding models."""
        assert "text-embedding-ada-002" in PRICING
        assert "input" in PRICING["text-embedding-ada-002"]
    
    def test_pricing_values_positive(self):
        """Test that all pricing values are positive."""
        for model, costs in PRICING.items():
            for cost_type, value in costs.items():
                assert value > 0, f"{model}.{cost_type} should be positive"


class TestCostAccuracy:
    """Test cost calculation accuracy."""
    
    def test_known_cost_gpt4(self):
        """Test cost calculation with known input."""
        # "Hello" is typically 1 token
        text = "Hello"
        tokens = count_tokens(text)
        input_cost, _, _ = calculate_generation_cost(tokens, 0, model="gpt-4")
        # Cost should be approximately tokens * price per 1k tokens
        expected = (tokens / 1000.0) * PRICING["gpt-4"]["input"]
        assert abs(input_cost - expected) < 0.0001
    
    def test_cost_proportional_to_length(self):
        """Test that cost is proportional to text length."""
        short_text = "Hello"
        long_text = "Hello " * 100
        
        short_tokens = count_tokens(short_text)
        long_tokens = count_tokens(long_text)
        
        cost_short = calculate_embedding_cost(short_tokens)
        cost_long = calculate_embedding_cost(long_tokens)
        
        # Long text should cost more
        assert cost_long > cost_short
        # And roughly proportional
        assert cost_long > cost_short * 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
