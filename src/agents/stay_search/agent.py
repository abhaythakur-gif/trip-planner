"""
Stay Search Agent - searches and selects accommodation options using SerpAPI Google Hotels.
"""

from typing import List

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...config import settings
from .tool import (
    search_real_hotels,
    generate_fallback_hotels,
    score_stay_options,
)


class StaySearchAgent(BaseAgent):
    """
    Searches for accommodation options using SerpAPI Google Hotels.

    Responsibilities:
    - Search for hotels using SerpAPI (real-time, works globally including India)
    - Score options based on constraints (price, location, quality, amenities)
    - Select optimal accommodation
    - Fallback to curated options if SerpAPI unavailable

    API: SerpAPI Google Hotels engine (100 searches/month free)
    """

    def __init__(self):
        super().__init__("stay_search")

    async def execute(self, state: TravelState) -> TravelState:
        """Search for accommodation options."""

        self.logger.info("Starting accommodation search")
        request = state.get("structured_request")
        budget = state.get("budget_allocation")
        constraints = state.get("constraints")

        if not request or not budget:
            error_msg = (
                f"Missing required data: request={request is not None}, budget={budget is not None}"
            )
            self.logger.error(error_msg)
            self.logger.debug(f"State keys: {list(state.keys())}")
            state["errors"].append(f"{self.name}: {error_msg}")
            return state

        self.logger.info(f"Searching accommodation in {request.destination}")
        self.logger.debug(
            f"Budget for accommodation: ${budget.stay}, duration: {request.duration_days} days"
        )

        # Try real hotels from SerpAPI
        self.logger.debug("Attempting to search hotels via SerpAPI Google Hotels")
        options = await search_real_hotels(request, budget, constraints, self.logger)

        if not options:
            self.logger.warning("No hotels found via SerpAPI, using fallback options")
            state["warnings"].append(
                "Using curated hotel options (SerpAPI unavailable or no results)"
            )
            options = generate_fallback_hotels(request, budget, constraints)
            self.logger.info(f"Generated {len(options)} fallback options")
        else:
            self.logger.info(f"Found {len(options)} hotel options from SerpAPI")

        # Score and rank
        scored_options = score_stay_options(options, budget, constraints)
        state["stay_options"] = scored_options

        if scored_options:
            state["selected_stay"] = scored_options[0]

            selected = state["selected_stay"]
            self.log_decision(
                state,
                decision=f"Selected {selected.name} for ${selected.total_price:.2f}",
                reasoning=f"Best score ({selected.score:.1f}), rating {selected.rating}/5",
                alternatives=len(scored_options) - 1,
            )

            self.logger.info(
                f"Selected stay: {selected.name} (score: {selected.score:.1f})"
            )
        else:
            state["warnings"].append("No accommodation options found")
            self.logger.warning("No accommodation options found")

        return state
