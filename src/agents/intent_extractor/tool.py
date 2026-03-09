"""
Tool functions for the Intent Extractor Agent.
"""

from typing import List


def generate_clarification_questions(missing_fields: List[str]) -> List[str]:
    """
    Generate clarification questions for missing travel request fields.

    Args:
        missing_fields: List of field names that are absent or incomplete.

    Returns:
        List of natural-language question strings.
    """
    questions = []
    for field in missing_fields:
        if field == "origin":
            questions.append("Where will you be traveling from?")
        elif "travel_dates" in field or "travel_month" in field:
            questions.append(
                "When would you like to travel? Please provide specific dates or a preferred month."
            )
        elif field == "destination":
            questions.append("Where would you like to go?")
        elif field == "budget_total":
            questions.append("What is your total budget for this trip?")
        elif field == "duration_days":
            questions.append("How many days would you like the trip to be?")
    return questions
