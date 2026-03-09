"""
Budget Allocator Agent - distributes budget across travel categories.
"""

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.budget import BudgetAllocation
from ...config import settings
from .tool import get_cost_multiplier, COST_MULTIPLIERS


class BudgetAllocatorAgent(BaseAgent):
    """
    Allocates total budget into transport, stay, food, activities, and buffer.

    Responsibilities:
    - Distribute budget based on destination cost of living
    - Adjust for trip duration
    - Consider travel style preferences
    - Maintain minimum buffer requirement
    """

    def __init__(self):
        super().__init__("budget_allocator")

    async def execute(self, state: TravelState) -> TravelState:
        """Allocate budget across categories."""

        self.logger.info("Starting budget allocation")
        request = state["structured_request"]
        constraints = state["constraints"]

        if not request or not constraints:
            self.logger.error(
                f"Missing required data: request={request is not None}, constraints={constraints is not None}"
            )
            self.logger.debug(f"State keys: {list(state.keys())}")
            return state

        total_budget = request.budget_total
        destination = request.destination.lower()
        duration = request.duration_days
        num_travelers = request.num_travelers

        self.logger.info(
            f"Allocating ${total_budget} budget for {duration} days, {num_travelers} travelers"
        )
        self.logger.debug(
            f"Destination: {destination}, Comfort level: {request.preferences.comfort_level}"
        )

        # Get cost multiplier for destination
        self.logger.debug(f"Looking up cost multiplier for destination: {destination}")
        cost_multiplier = get_cost_multiplier(destination, COST_MULTIPLIERS)
        self.logger.info(f"Cost multiplier for {destination}: {cost_multiplier:.2f}")

        # Base allocation percentages
        self.logger.debug("Determining allocation percentages based on comfort level")
        if request.preferences.comfort_level <= 2:
            self.logger.debug("Using budget travel allocation (comfort <= 2)")
            transport_pct = 0.35
            stay_pct = 0.30
            food_pct = 0.20
            activities_pct = 0.10
            buffer_pct = 0.05
        elif request.preferences.comfort_level >= 4:
            self.logger.debug("Using luxury travel allocation (comfort >= 4)")
            transport_pct = 0.30
            stay_pct = 0.40
            food_pct = 0.15
            activities_pct = 0.10
            buffer_pct = 0.05
        else:
            transport_pct = 0.32
            stay_pct = 0.35
            food_pct = 0.18
            activities_pct = 0.10
            buffer_pct = 0.05

        # Adjust for destination cost
        if cost_multiplier > 1.2:
            stay_pct += 0.05
            food_pct += 0.03
            activities_pct -= 0.03
            buffer_pct -= 0.05
        elif cost_multiplier < 0.7:
            activities_pct += 0.05
            buffer_pct += 0.05
            stay_pct -= 0.05
            food_pct -= 0.05

        # Ensure buffer meets minimum
        min_buffer = settings.min_buffer_percentage
        if buffer_pct < min_buffer:
            diff = min_buffer - buffer_pct
            buffer_pct = min_buffer
            activities_pct -= diff

        # Calculate amounts
        allocation = BudgetAllocation(
            total=total_budget,
            currency=request.currency,
            transport=round(total_budget * transport_pct, 2),
            stay=round(total_budget * stay_pct, 2),
            food=round(total_budget * food_pct, 2),
            activities=round(total_budget * activities_pct, 2),
            buffer=round(total_budget * buffer_pct, 2),
        )

        # Ensure sum equals total (adjust for rounding)
        diff = total_budget - allocation.allocated_total
        if abs(diff) > 0.01:
            allocation.buffer += diff

        state["budget_allocation"] = allocation

        self.log_decision(
            state,
            decision=(
                f"Allocated budget: Transport ${allocation.transport}, "
                f"Stay ${allocation.stay}, Food ${allocation.food}, "
                f"Activities ${allocation.activities}, Buffer ${allocation.buffer}"
            ),
            reasoning=(
                f"Based on {destination} cost multiplier {cost_multiplier:.2f} "
                f"and {request.preferences.comfort_level}/5 comfort level"
            ),
            alternatives=1,
        )

        self.logger.info(
            f"Budget allocation complete. Buffer: ${allocation.buffer} ({buffer_pct * 100:.1f}%)"
        )

        return state
