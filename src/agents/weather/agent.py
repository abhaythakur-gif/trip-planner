"""
Weather Agent - fetches and analyzes weather data using Open-Meteo API.
"""

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from .tool import fetch_real_weather, generate_fallback_weather


class WeatherAgent(BaseAgent):
    """
    Fetches weather data and assesses weather risks.

    Responsibilities:
    - Fetch weather forecast for destination and dates
    - Assess weather risks
    - Identify good/bad days for outdoor activities
    - Provide recommendations

    Uses Open-Meteo API (free, no API key required)
    - Up to 16 days forecast
    - 10,000 requests per day
    """

    def __init__(self):
        super().__init__("weather")

    async def execute(self, state: TravelState) -> TravelState:
        """Fetch weather data using Open-Meteo API."""

        self.logger.info("Starting weather data fetch")
        request = state.get("structured_request")

        if not request:
            error_msg = "Missing required data: structured_request"
            self.logger.error(error_msg)
            state["errors"].append(f"{self.name}: {error_msg}")
            return state

        self.logger.info(f"Fetching weather for {request.destination}")
        city = request.destination.split(",")[0].strip()

        weather_data = await fetch_real_weather(city, request, self.logger)

        if not weather_data:
            self.logger.warning("Real weather API unavailable, using fallback data")
            state["warnings"].append("Real-time weather data unavailable, using estimates")
            weather_data = generate_fallback_weather(request)

        state["weather_data"] = weather_data

        outdoor_days = len(weather_data.outdoor_activity_days)
        total_days = len(weather_data.forecasts)

        self.log_decision(
            state,
            decision=f"Weather forecast retrieved: {outdoor_days}/{total_days} good outdoor days",
            reasoning=f"Overall risk: {weather_data.risk_assessment.overall_risk}",
            alternatives=0,
        )

        self.logger.info(f"Weather data: {outdoor_days}/{total_days} outdoor-friendly days")
        return state
