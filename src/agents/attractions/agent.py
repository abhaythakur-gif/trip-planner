"""
Attractions Agent - searches and categorizes tourist attractions using free APIs.
Uses OpenTripMap for attractions and Overpass API (OSM) for general POIs.
"""

import asyncio
from typing import List

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.agent_outputs import AttractionList
from .tool import (
    get_city_coordinates,
    search_real_attractions,
    generate_fallback_attractions,
    score_attractions,
    categorize_attractions,
)


class AttractionsAgent(BaseAgent):
    """
    Searches for tourist attractions and activities.

    Responsibilities:
    - Search for attractions based on destination and preferences
    - Categorize by type (museums, restaurants, parks, etc.)
    - Score based on ratings, reviews, and user preferences
    - Organize indoor/outdoor options

    Uses:
    - SerpAPI Google Maps: Real-world tourist attractions (100/month free)
    - Nominatim: Geocoding (no key required)
    - CITY_DATA fallback: Curated local data for popular destinations
    """

    def __init__(self):
        super().__init__("attractions")

    async def execute(self, state: TravelState) -> TravelState:
        """Search for attractions using free APIs (OpenTripMap + Overpass)."""

        self.logger.info("Starting attractions search")
        request = state.get("structured_request")
        constraints = state.get("constraints")

        if not request:
            error_msg = "Missing required data: structured_request"
            self.logger.error(error_msg)
            self.logger.debug(f"State keys: {list(state.keys())}")
            state["errors"].append(f"{self.name}: {error_msg}")
            return state

        self.logger.info(f"Searching attractions in {request.destination}")
        self.logger.debug(
            f"User interests: {request.preferences.interests if request.preferences else 'None'}"
        )

        try:
            # Get city coordinates
            self.logger.debug("Getting city coordinates")
            city = request.destination.split(",")[0].strip()
            coordinates = await get_city_coordinates(city, self.logger)
            self.logger.debug(f"Coordinates for {city}: {coordinates}")

            # Search for real attractions
            self.logger.debug("Searching for attractions via APIs")
            all_attractions = await search_real_attractions(
                city, coordinates, constraints, self.logger
            )

            # If API fails, use fallback
            if not all_attractions:
                self.logger.warning("No attractions from API, using fallback data")
                state["warnings"].append(
                    "Real-time attraction data unavailable, using popular destinations"
                )
                all_attractions = generate_fallback_attractions(request, constraints)
                self.logger.info(f"Generated {len(all_attractions)} fallback attractions")
            else:
                self.logger.info(f"Found {len(all_attractions)} attractions from APIs")

            # Score and categorize
            self.logger.debug("Scoring and categorizing attractions")
            scored_attractions = score_attractions(all_attractions, constraints)
            categorized = categorize_attractions(scored_attractions)
            self.logger.info(
                f"Categorized {len(scored_attractions)} attractions into groups"
            )
            self.logger.debug(
                f"Categories: top_rated={len(categorized.top_rated)}, "
                f"outdoor={len(categorized.outdoor_activities)}, "
                f"indoor={len(categorized.indoor_activities)}"
            )

            # Store attractions
            state["attractions"] = categorized

            # Log decision
            self.log_decision(
                state,
                decision=f"Found {len(scored_attractions)} attractions",
                reasoning=f"Top rated: {categorized.top_rated[0].name if categorized.top_rated else 'N/A'}",
                alternatives=len(scored_attractions),
            )

            self.logger.info(f"Found {len(scored_attractions)} attractions")

        except Exception as e:
            error_msg = f"Error in attractions processing: {type(e).__name__}: {str(e)}"
            self.logger.error(error_msg)
            state["warnings"].append("Using fallback attraction data due to processing error")

            try:
                fallback_attractions = generate_fallback_attractions(request, constraints)
                scored_attractions = score_attractions(fallback_attractions, constraints)
                categorized = categorize_attractions(scored_attractions)
                state["attractions"] = categorized
                self.logger.info(f"Using {len(scored_attractions)} fallback attractions")
            except Exception as fallback_error:
                self.logger.error(f"Even fallback failed: {fallback_error}")
                state["attractions"] = AttractionList(
                    all_attractions=[],
                    top_rated=[],
                    budget_friendly=[],
                    outdoor_activities=[],
                    indoor_activities=[],
                )

        return state
