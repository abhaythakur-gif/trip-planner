"""
Prompt templates for the Constraint Modeler Agent.
"""

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


def get_constraint_modeling_prompt(request: dict, config: dict) -> str:
    """Return the constraint modeling prompt formatted with request details."""
    return CONSTRAINT_MODELING_PROMPT.format(
        request=request,
        min_buffer_pct=config.get("min_buffer_percentage", 0.05) * 100,
        max_replan=config.get("max_replan_attempts", 3),
        budget=request.get("budget_total"),
        duration=request.get("duration_days"),
        start_date=request.get("travel_dates", {}).get("start") if request.get("travel_dates") else "TBD",
        end_date=request.get("travel_dates", {}).get("end") if request.get("travel_dates") else "TBD",
    )
