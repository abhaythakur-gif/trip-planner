"""
Unit tests for Budget Allocator Agent.
"""

import pytest

from src.agents.budget_allocator import BudgetAllocatorAgent
from src.schemas.state import create_initial_state
from src.schemas.request import TravelRequest, TravelPreferences


@pytest.mark.unit
@pytest.mark.asyncio
async def test_budget_allocation_basic(sample_travel_request):
    """Test basic budget allocation."""
    
    agent = BudgetAllocatorAgent()
    
    # Create state with request
    state = create_initial_state("test")
    state["structured_request"] = sample_travel_request
    
    # Create simple constraints
    from src.schemas.constraints import ConstraintSet, HardConstraints, SoftConstraints
    from datetime import date
    
    state["constraints"] = ConstraintSet(
        hard=HardConstraints(
            max_budget=2500.0,
            duration_days=5,
            date_start=date.today(),
            date_end=date.today()
        ),
        soft=SoftConstraints()
    )
    
    # Run agent
    result = await agent.execute(state)
    
    # Assertions
    assert result["budget_allocation"] is not None
    allocation = result["budget_allocation"]
    
    # Check total equals budget
    assert abs(allocation.total - 2500.0) < 0.01
    assert abs(allocation.allocated_total - 2500.0) < 0.01
    
    # Check all categories have allocations
    assert allocation.transport > 0
    assert allocation.stay > 0
    assert allocation.food > 0
    assert allocation.activities > 0
    assert allocation.buffer > 0
    
    # Check buffer meets minimum (5%)
    assert allocation.buffer >= 2500.0 * 0.05


@pytest.mark.unit
@pytest.mark.asyncio
async def test_budget_allocation_expensive_destination():
    """Test budget allocation adjusts for expensive destinations."""
    
    agent = BudgetAllocatorAgent()
    
    # Create request for expensive city (London)
    request = TravelRequest(
        destination="London",
        duration_days=5,
        budget_total=3000.0,
        currency="USD",
        num_travelers=1,
        origin="New York",
        preferences=TravelPreferences(comfort_level=3)
    )
    
    state = create_initial_state("test")
    state["structured_request"] = request
    
    from src.schemas.constraints import ConstraintSet, HardConstraints, SoftConstraints
    from datetime import date
    
    state["constraints"] = ConstraintSet(
        hard=HardConstraints(
            max_budget=3000.0,
            duration_days=5,
            date_start=date.today(),
            date_end=date.today()
        ),
        soft=SoftConstraints()
    )
    
    result = await agent.execute(state)
    allocation = result["budget_allocation"]
    
    # London should have higher stay allocation
    # For expensive destinations, stay % should be higher than default
    stay_percent = allocation.stay / allocation.total
    assert stay_percent > 0.35  # Should be adjusted upward


@pytest.mark.unit
def test_cost_multiplier_lookup():
    """Test cost multiplier lookup for destinations."""
    
    agent = BudgetAllocatorAgent()
    
    # Test known expensive cities
    assert agent._get_cost_multiplier("london") > 1.0
    assert agent._get_cost_multiplier("tokyo") > 1.0
    
    # Test known cheap cities
    assert agent._get_cost_multiplier("bangkok") < 1.0
    assert agent._get_cost_multiplier("bali") < 1.0
    
    # Test unknown destination (should return default 1.0)
    assert agent._get_cost_multiplier("unknown_city") == 1.0
