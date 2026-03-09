"""
LLM prompt templates for various agents.

NOTE: Prompt functions have moved to src/agents/prompts/.
The imports below preserve backward compatibility for any code that still does:
    from src.utils.prompts import get_intent_extraction_prompt
"""

# ---------------------------------------------------------------------------
# Backward-compatibility re-exports from the new canonical locations
# ---------------------------------------------------------------------------
from ..agents.prompts.intent_extractor import (   # noqa: F401
    INTENT_EXTRACTION_PROMPT,
    get_intent_extraction_prompt,
)
from ..agents.prompts.constraint_modeler import (  # noqa: F401
    CONSTRAINT_MODELING_PROMPT,
    get_constraint_modeling_prompt,
)
# ---------------------------------------------------------------------------

INTENT_EXTRACTION_PROMPT = """You are an expert travel planning assistant. Your task is to extract structured travel information from a user's natural language request.

Extract the following information from the user's query:
- **destination**: Primary destination city or country
- **duration_days**: How many days the trip will last
- **budget_total**: Total budget amount (extract the number)
- **currency**: Currency code (USD, EUR, etc.)
- **travel_dates**: Specific dates if mentioned (start and end)
- **travel_month**: Month name (e.g., "march", "april") or relative expression (e.g., "next month", "this month")
- **num_travelers**: Number of people traveling
- **origin**: Starting city/location
- **flexibility**: Whether the user is flexible with dates/budget
- **preferences**: Travel style, interests, accommodation preferences, pace, etc.

User Query: {query}

If any REQUIRED information is missing (destination, duration, budget, dates/month, origin), set those fields to null and we'll request clarification.

Return ONLY valid JSON matching this schema:
{{
    "destination": "string",
    "duration_days": int,
    "budget_total": float,
    "currency": "USD",
    "travel_dates": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} or null,
    "travel_month": "month name or relative expression" or null,
    "num_travelers": int,
    "origin": "string" or null,
    "flexibility": boolean,
    "preferences": {{
        "travel_style": ["list of styles"],
        "interests": ["list"],
        "accommodation_type": ["hotel", etc.],
        "pace": "relaxed"|"moderate"|"packed",
        "comfort_level": 1-5,
        "risk_tolerance": 1-5
    }},
    "special_requirements": ["list"]
}}

IMPORTANT: Return ONLY the JSON object, no explanation or additional text."""

CONSTRAINT_MODELING_PROMPT = """You are a constraint modeling expert. Convert the travel request into hard and soft constraints.

Travel Request:
{request}

System Configuration:
- Minimum buffer percentage: {min_buffer_pct}
- Maximum replan attempts: {max_replan}

Create:
1. **Hard Constraints** (non-negotiable):
   - max_budget: {budget}
   - min_budget_buffer: {min_buffer_pct}
   - duration_days: {duration}
   - date_start: {start_date}
   - date_end: {end_date}
   - max_flight_duration_hours: reasonable limit
   - max_connections: reasonable limit

2. **Soft Constraints** (preferences):
   - comfort_level: based on budget and preferences
   - risk_tolerance: based on traveler profile
   - pace: from preferences
   - accommodation preferences
   - activity preferences

Return ONLY valid JSON matching the ConstraintSet schema."""

BUDGET_ALLOCATION_PROMPT = """You are a budget allocation expert. Distribute the total budget across categories.

Travel Details:
- Destination: {destination}
- Duration: {duration_days} days
- Total Budget: ${total_budget}
- Number of Travelers: {num_travelers}
- Travel Style: {travel_style}

Standard allocation percentages:
- Transport: 30-35%
- Stay: 30-40%
- Food: 15-25%
- Activities: 10-15%
- Buffer: 5-10% (minimum {min_buffer_pct}%)

Adjust based on:
1. Destination cost of living (expensive cities → higher stay %)
2. Trip duration (longer trips → lower per-day costs)
3. Travel style (luxury → higher comfort, budget → optimize costs)
4. Number of travelers (groups may get discounts)

IMPORTANT: 
- total must equal sum of all allocations
- buffer must be at least {min_buffer_pct}% of total
- all amounts must be positive

Return ONLY valid JSON:
{{
    "total": {total_budget},
    "currency": "USD",
    "transport": float,
    "stay": float,
    "food": float,
    "activities": float,
    "buffer": float
}}"""

TRANSPORT_SEARCH_PROMPT = """You are evaluating transport options for a trip.

Trip Details:
- Origin: {origin}
- Destination: {destination}
- Departure: {departure_date}
- Return: {return_date}
- Budget: ${transport_budget}
- Travelers: {num_travelers}

Scoring Criteria (weights):
- Cost (40%): Lower is better
- Duration (25%): Shorter is better
- Flexibility (20%): Refundable/changeable is better
- Comfort (15%): Better class/fewer stops is better

For each option, calculate a score 0-100 where:
- Cost score: 100 * (1 - price/budget_max)
- Duration score: 100 * (1 - duration/24hrs)
- Flexibility score: 100 if refundable, 50 if changeable, 0 if non-refundable
- Comfort score: economy=60, premium=75, business=90, first=100, -10 per connection

Final score = weighted sum of criteria scores."""

STAY_SEARCH_PROMPT = """You are evaluating accommodation options.

Trip Details:
- Destination: {destination}
- Check-in: {checkin_date}
- Check-out: {checkout_date}
- Nights: {num_nights}
- Budget per night: ${budget_per_night}
- Travelers: {num_travelers}
- Preferences: {preferences}

Scoring Criteria (weights):
- Price (35%): Lower is better
- Rating (25%): Higher is better
- Location (25%): Closer to center is better
- Cancellation (15%): Free cancellation is better

For each option, calculate score 0-100."""

ITINERARY_BUILDING_PROMPT = """You are a trip itinerary expert. Build a detailed day-by-day itinerary.

Requirements:
1. Balance activities across days (3-4 per day for moderate pace)
2. Schedule outdoor activities on good weather days
3. Indoor activities on poor weather days
4. Minimize travel time between locations (cluster geographically)
5. Respect opening hours and best visit times
6. Leave buffer time between activities (30 mins minimum)
7. Include meal times (breakfast, lunch, dinner)
8. Stay within daily budget allocation

Trip Details:
- Arrival: {arrival_time}
- Departure: {departure_time}
- Accommodation: {hotel_location}
- Weather: {weather_data}
- Available attractions: {attractions}
- Daily activity budget: ${daily_budget}

Build a complete itinerary with time slots, activities, meals, and notes."""

RISK_ASSESSMENT_PROMPT = """You are a risk assessment expert. Evaluate risks for this travel plan.

Plan Details:
{plan_summary}

Evaluate these scenarios:
1. **Weather Deterioration**: What if weather is 50% worse than forecast?
2. **Transport Delay**: What if flight is delayed 4 hours?
3. **Budget Overrun**: What if actual costs are 20% higher?

For each scenario:
- Estimate probability (0-1)
- Assess impact severity (low/medium/high)
- Identify affected components
- Provide fallback recommendations
- Estimate additional costs

Calculate overall risk score (0-100) based on:
- Weather risk (30%)
- Transport risk (25%)
- Budget risk (25%)
- Destination safety (20%)

Return structured risk assessment."""

CONFIDENCE_SCORING_PROMPT = """You are a plan confidence calculator.

Plan Metrics:
- Budget buffer: ${buffer} ({buffer_pct}% of total)
- Data completeness: {completeness_pct}%
- Constraint violations: {violations}
- Risk score: {risk_score}/100
- Replan count: {replan_count}/3

Calculate confidence score (0-100):
- Budget score (30%): 100 if buffer >= 10%, proportional if less
- Completeness score (25%): Based on data completeness
- Risk score (25%): 100 - risk_score
- Violation score (20%): 100 if no violations, 50 if minor, 0 if major

Confidence = weighted average of scores

Provide:
1. Final confidence score (0-100)
2. Explanation of why this score
3. Main factors affecting confidence
4. Whether plan should be accepted or replanned (threshold: 70)

Return JSON with score and explanation."""

def get_intent_extraction_prompt(query: str) -> str:
    """Get formatted intent extraction prompt."""
    return INTENT_EXTRACTION_PROMPT.format(query=query)

def get_constraint_modeling_prompt(request: dict, config: dict) -> str:
    """Get formatted constraint modeling prompt."""
    return CONSTRAINT_MODELING_PROMPT.format(
        request=request,
        min_buffer_pct=config.get("min_buffer_percentage", 0.05) * 100,
        max_replan=config.get("max_replan_attempts", 3),
        budget=request.get("budget_total"),
        duration=request.get("duration_days"),
        start_date=request.get("travel_dates", {}).get("start") if request.get("travel_dates") else "TBD",
        end_date=request.get("travel_dates", {}).get("end") if request.get("travel_dates") else "TBD"
    )

def get_budget_allocation_prompt(request: dict, min_buffer_pct: float) -> str:
    """Get formatted budget allocation prompt."""
    prefs = request.get("preferences", {})
    return BUDGET_ALLOCATION_PROMPT.format(
        destination=request.get("destination", ""),
        duration_days=request.get("duration_days", 0),
        total_budget=request.get("budget_total", 0),
        num_travelers=request.get("num_travelers", 1),
        travel_style=prefs.get("travel_style", []),
        min_buffer_pct=min_buffer_pct * 100
    )
