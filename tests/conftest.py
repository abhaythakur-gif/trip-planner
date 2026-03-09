"""
Test configuration and fixtures.
"""

import pytest
from datetime import date, timedelta

from src.schemas.request import TravelRequest, TravelPreferences, DateRange
from src.schemas.state import TravelState, create_initial_state


@pytest.fixture
def sample_query():
    """Sample travel query."""
    return "Plan a 5-day trip to Paris in May for $2500 from New York"


@pytest.fixture
def sample_travel_request():
    """Sample complete travel request."""
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=5)
    
    return TravelRequest(
        destination="Paris",
        duration_days=5,
        budget_total=2500.0,
        currency="USD",
        travel_dates=DateRange(start=start, end=end),
        num_travelers=1,
        origin="New York",
        preferences=TravelPreferences(
            comfort_level=3,
            pace="moderate"
        )
    )


@pytest.fixture
def initial_state(sample_query):
    """Initial travel state."""
    return create_initial_state(sample_query)


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "destination": "Paris",
        "duration_days": 5,
        "budget_total": 2500.0,
        "currency": "USD",
        "travel_dates": None,
        "travel_month": "may",
        "num_travelers": 1,
        "origin": "New York",
        "flexibility": False,
        "preferences": {
            "travel_style": ["cultural"],
            "interests": ["museums", "food"],
            "accommodation_type": ["hotel"],
            "pace": "moderate",
            "comfort_level": 3,
            "risk_tolerance": 3
        },
        "special_requirements": []
    }
