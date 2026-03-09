"""
Tool functions for the Question Generator Agent.
"""

from typing import List

from ...schemas.conversation import RequiredTripFields

FIELD_PRIORITY = ["destination", "start_date", "duration", "budget", "origin", "travelers"]

TEMPLATE_QUESTIONS = {
    "destination": "Where would you like to travel to?",
    "origin": "Which city will you be traveling from?",
    "start_date": "When would you like to start your trip?",
    "duration": "How many days would you like to stay?",
    "budget": "What's your approximate budget for this trip?",
    "travelers": "How many people will be traveling?",
}


def get_next_priority_field(missing_fields: List[str]) -> str:
    """Return the highest-priority missing field."""
    for field in FIELD_PRIORITY:
        if field in missing_fields:
            return field
    return missing_fields[0]


def get_template_question(field: str, accumulated_fields: RequiredTripFields) -> str:
    """Return a context-aware template question for the given field."""
    question = TEMPLATE_QUESTIONS.get(field, f"Could you tell me about your {field}?")

    destination = accumulated_fields.destination
    if field != "destination" and destination:
        if field == "start_date":
            question = f"When would you like to visit {destination}?"
        elif field == "duration":
            question = f"How many days would you like to spend in {destination}?"
        elif field == "budget":
            question = f"What's your budget for visiting {destination}?"

    return question
