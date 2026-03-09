"""
Prompt templates for the Intent Extractor Agent.
"""

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


def get_intent_extraction_prompt(query: str) -> str:
    """Return the intent extraction prompt formatted with the user query."""
    return INTENT_EXTRACTION_PROMPT.format(query=query)
