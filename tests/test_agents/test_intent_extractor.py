"""
Unit tests for Intent Extractor Agent.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from src.agents.intent_extractor import IntentExtractorAgent
from src.schemas.state import create_initial_state


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_extractor_complete_request(mock_llm_response):
    """Test intent extraction with complete request."""
    
    # Create agent
    agent = IntentExtractorAgent()
    
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = json.dumps(mock_llm_response)
    
    with patch.object(agent.llm, 'ainvoke', return_value=mock_response):
        # Create state
        state = create_initial_state("Plan a 5-day trip to Paris in May for $2500 from New York")
        
        # Run agent
        result = await agent.execute(state)
        
        # Assertions
        assert result["structured_request"] is not None
        assert result["structured_request"].destination == "Paris"
        assert result["structured_request"].duration_days == 5
        assert result["structured_request"].budget_total == 2500.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_extractor_incomplete_request():
    """Test intent extraction with incomplete request (missing origin)."""
    
    agent = IntentExtractorAgent()
    
    # Incomplete request (no origin)
    incomplete_response = {
        "destination": "Paris",
        "duration_days": 5,
        "budget_total": 2500.0,
        "currency": "USD",
        "travel_dates": None,
        "travel_month": "may",
        "num_travelers": 1,
        "origin": None,  # Missing!
        "flexibility": False,
        "preferences": {
            "travel_style": [],
            "interests": [],
            "accommodation_type": ["hotel"],
            "pace": "moderate",
            "comfort_level": 3,
            "risk_tolerance": 3
        },
        "special_requirements": []
    }
    
    mock_response = MagicMock()
    mock_response.content = json.dumps(incomplete_response)
    
    with patch.object(agent.llm, 'ainvoke', return_value=mock_response):
        state = create_initial_state("Plan a 5-day trip to Paris in May for $2500")
        
        result = await agent.execute(state)
        
        # Should require clarification
        assert result["requires_clarification"] is True
        assert result["clarification"] is not None
        assert "origin" in result["clarification"].missing_fields


@pytest.mark.unit
def test_generate_clarification_questions():
    """Test clarification question generation."""
    
    agent = IntentExtractorAgent()
    
    missing = ["origin", "travel_dates or travel_month"]
    questions = agent._generate_questions(missing)
    
    assert len(questions) == 2
    assert any("traveling from" in q.lower() for q in questions)
    assert any("when" in q.lower() for q in questions)
