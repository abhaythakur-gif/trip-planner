"""
Transport Search Agent - searches and selects transport options using SerpAPI (Google Flights).
"""

from typing import List, Optional

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.agent_outputs import TransportOption
from ...config import settings
from .tool import (
    get_airport_code,
    search_real_flights,
    generate_fallback_transport,
    score_transport_options,
    build_return_flight,
)


class TransportSearchAgent(BaseAgent):
    """
    Searches for transport options (flights) using SerpAPI Google Flights.

    Responsibilities:
    - Search for real flight options based on route and dates
    - Score options based on constraints (price, time, quality)
    - Select optimal outbound and return transport
    - Falls back to estimates if SerpAPI is unavailable

    API: SerpAPI Google Flights engine (works globally including India)
    """

    def __init__(self):
        super().__init__("transport_search")

    async def execute(self, state: TravelState) -> TravelState:
        """Search for transport options using SerpAPI Google Flights."""

        self.logger.info("Starting transport search")
        request = state.get("structured_request")
        budget = state.get("budget_allocation")

        if not request or not budget:
            error_msg = f"Missing required data: request={request is not None}, budget={budget is not None}"
            self.logger.error(error_msg)
            self.logger.debug(f"State keys: {list(state.keys())}")
            state["errors"].append(f"{self.name}: {error_msg}")
            return state

        self.logger.info(f"Searching flights from {request.origin} to {request.destination}")
        self.logger.debug(f"Transport budget: ${budget.transport}, travelers: {request.num_travelers}")

        if not request.start_date:
            self.logger.error("No travel dates available in request")
            state["errors"].append("Transport search requires travel dates")
            return state

        self.logger.debug(
            f"Travel dates: {request.start_date} to "
            f"{request.travel_dates.end if request.travel_dates else 'N/A'}"
        )

        # Resolve IATA codes
        self.logger.debug("Converting city names to IATA airport codes")
        origin_code = get_airport_code(request.origin)
        dest_code = get_airport_code(request.destination)
        self.logger.debug(f"Airport codes: {request.origin} -> {origin_code}, {request.destination} -> {dest_code}")

        # Search for real flights
        self.logger.debug("Searching for flights via SerpAPI Google Flights")
        real_options = await search_real_flights(
            origin_code, dest_code, request, budget, self.logger
        )

        if not real_options:
            self.logger.warning("No flights from SerpAPI, using fallback estimates")
            state["warnings"].append("Real-time flight data unavailable, using estimates")
            real_options = generate_fallback_transport(request, budget)
            self.logger.info(f"Generated {len(real_options)} fallback flight options")
        else:
            self.logger.info(f"Found {len(real_options)} flight options from SerpAPI")

        # Score and rank
        scored_options = score_transport_options(real_options, budget.transport)
        state["transport_options"] = scored_options

        if scored_options:
            state["selected_transport_outbound"] = scored_options[0]
            state["selected_transport_return"] = build_return_flight(scored_options[0], request)

            outbound = state["selected_transport_outbound"]
            return_flight = state["selected_transport_return"]

            self.log_decision(
                state,
                decision=f"Selected {outbound.carrier} for ${outbound.price + return_flight.price:.2f}",
                reasoning=f"Best score ({outbound.score:.1f}) within budget",
                alternatives=len(scored_options) - 1,
            )

            self.logger.info(
                f"Selected transport: {outbound.carrier} (score: {outbound.score:.1f})"
            )
        else:
            state["warnings"].append("No transport options found")
            self.logger.warning("No transport options found")

        return state
