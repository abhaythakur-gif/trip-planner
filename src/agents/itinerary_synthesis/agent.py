"""
Itinerary Synthesis Agent - creates day-by-day itinerary.
"""

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.agent_outputs import MultiDayItinerary
from .tool import build_full_itinerary, resolve_day_weather, create_daily_itinerary, build_activities, build_meals, build_activity_pool, pick_day_attractions


class ItinerarySynthesisAgent(BaseAgent):
    """
    Synthesizes a complete day-by-day itinerary.

    Responsibilities:
    - Combine transport, stay, weather, and attractions into cohesive plan
    - Optimize daily schedules for efficiency
    - Balance activity levels across days
    - Schedule meals and rest periods
    - Consider weather for outdoor/indoor activity placement
    - Respect opening hours and booking requirements
    """

    def __init__(self):
        super().__init__("itinerary_synthesis")

    async def execute(self, state: TravelState) -> TravelState:
        """Synthesize complete itinerary."""

        self.logger.info("Starting itinerary synthesis")
        request = state.get("structured_request")
        weather = state.get("weather_data")
        attractions_list = state.get("attractions")
        budget = state.get("budget_allocation")

        missing = []
        if not request:
            missing.append("structured_request")
        if not weather:
            missing.append("weather_data")
        if not attractions_list:
            missing.append("attractions")
        if not budget:
            missing.append("budget_allocation")

        if missing:
            error_msg = f"Missing required data for itinerary synthesis: {', '.join(missing)}"
            self.logger.error(error_msg)
            state["errors"].append(f"{self.name}: {error_msg}")

            if request:
                self.logger.info("Creating minimal itinerary with available data")
                return self._create_minimal_itinerary(state, request, attractions_list, weather, budget)

            self.logger.warning("Creating empty itinerary placeholder")
            state["itinerary"] = MultiDayItinerary(days=[], total_cost=0.0)
            return state

        self.logger.info(f"Synthesizing {request.duration_days or 7}-day itinerary")

        itinerary = build_full_itinerary(request, weather, attractions_list, budget, self.logger)
        state["itinerary"] = itinerary

        self.log_decision(
            state,
            decision=f"Created {len(itinerary.days)}-day itinerary",
            reasoning=f"Total activities: {sum(len(d.activities) for d in itinerary.days)}",
            alternatives=0,
        )
        self.logger.info(f"Itinerary created: {len(itinerary.days)} days, ${itinerary.total_cost:.2f} total")
        return state

    def _create_minimal_itinerary(
        self, state: TravelState, request, attractions_list, weather, budget
    ) -> TravelState:
        """Create a minimal itinerary when some data is missing."""
        from datetime import date as date_cls, timedelta
        from datetime import time

        self.logger.info(f"Creating minimal itinerary for {request.duration_days} days")

        all_attractions = []
        if attractions_list:
            all_attractions = attractions_list.all_attractions or attractions_list.top_rated or []

        current_date = request.start_date if request.start_date else date_cls.today()
        duration_days = request.duration_days or 7

        daily_itineraries = []
        total_cost = 0.0

        for day_num in range(1, duration_days + 1):
            day_date = current_date + timedelta(days=day_num - 1)
            day_weather = resolve_day_weather(weather, day_num, day_date)

            # Pick attractions using simple slicing
            start_idx = ((day_num - 1) * 3) % len(all_attractions) if all_attractions else 0
            day_attractions = all_attractions[start_idx: start_idx + 3] if all_attractions else []
            activities = build_activities(day_attractions)

            from ...schemas.agent_outputs import Meal, DailyItinerary
            meals = [
                Meal(type="breakfast", location="Hotel", estimated_cost=15.0, time=time(8, 0)),
                Meal(type="lunch", location="Local Restaurant", estimated_cost=25.0, time=time(13, 0)),
                Meal(type="dinner", location="Restaurant", estimated_cost=40.0, time=time(19, 30)),
            ]

            activity_cost = sum(a.attraction.cost for a in activities) if activities else 0
            meal_cost = sum(m.estimated_cost for m in meals)

            daily = DailyItinerary(
                day_number=day_num,
                date=day_date,
                weather=day_weather,
                activities=activities,
                meals=meals,
                total_cost=activity_cost + meal_cost,
                total_walking_distance_km=len(activities) * 2.5,
                estimated_transit_time_hours=len(activities) * 0.33,
                notes=["Minimal itinerary created with limited data"],
            )
            daily_itineraries.append(daily)
            total_cost += daily.total_cost

        itinerary = MultiDayItinerary(days=daily_itineraries, total_cost=total_cost)
        state["itinerary"] = itinerary
        state["warnings"].append("Itinerary created with incomplete data - some details may be missing")

        self.log_decision(
            state,
            decision=f"Created minimal {len(daily_itineraries)}-day itinerary",
            reasoning="Created with limited available data",
            alternatives=0,
        )
        self.logger.info(f"Minimal itinerary created: {len(daily_itineraries)} days")
        return state
