"""
Tool functions for the Optimization Agent.
Provides standalone budget/schedule validation and data completeness checks.
"""

from typing import List


def validate_budget(state: dict) -> List[str]:
    """
    Validate budget consistency across all plan components.

    Returns:
        List of issue strings (empty means no issues).
    """
    issues = []
    budget = state.get("budget_allocation")

    if not budget:
        issues.append("Budget allocation missing")
        return issues

    transport_out = state.get("selected_transport_outbound")
    transport_ret = state.get("selected_transport_return")

    if transport_out and transport_ret:
        total_transport = transport_out.price + transport_ret.price
        if total_transport > budget.transport * 1.1:
            issues.append(
                f"Transport cost ${total_transport:.2f} exceeds budget ${budget.transport:.2f}"
            )

    stay = state.get("selected_stay")
    if stay:
        if stay.total_price > budget.stay * 1.1:
            issues.append(
                f"Accommodation cost ${stay.total_price:.2f} exceeds budget ${budget.stay:.2f}"
            )

    itinerary = state.get("itinerary")
    if itinerary:
        if itinerary.total_cost > budget.total * 0.8:
            issues.append(
                f"Itinerary cost ${itinerary.total_cost:.2f} is high relative to budget"
            )

    return issues


def validate_schedule(state: dict) -> List[str]:
    """
    Validate schedule feasibility (no overlaps, reasonable transit times).

    Returns:
        List of issue strings.
    """
    issues = []
    itinerary = state.get("itinerary")

    if not itinerary:
        return issues

    for day in itinerary.days:
        if day.is_overloaded:
            issues.append(
                f"Day {day.day_number} may be overloaded: {len(day.activities)} activities"
            )

        if day.estimated_transit_time_hours > 4:
            issues.append(
                f"Day {day.day_number} has excessive transit time: {day.estimated_transit_time_hours:.1f}h"
            )

        for i, activity in enumerate(day.activities[:-1]):
            next_activity = day.activities[i + 1]
            if activity.time_end > next_activity.time_start:
                issues.append(
                    f"Day {day.day_number}: Activities overlap at {activity.time_end}"
                )

    return issues


def check_completeness(state: dict) -> float:
    """
    Return data completeness as a percentage (0–100).
    """
    required_fields = [
        "structured_request",
        "constraints",
        "budget_allocation",
        "selected_transport_outbound",
        "selected_transport_return",
        "selected_stay",
        "weather_data",
        "attractions",
        "itinerary",
    ]
    complete_count = sum(1 for f in required_fields if state.get(f) is not None)
    return (complete_count / len(required_fields)) * 100


def calculate_budget_deviation(state: dict) -> float:
    """
    Return budget deviation as a percentage (positive = over budget).
    """
    budget = state.get("budget_allocation")
    if not budget:
        return 0.0

    actual_spending = 0.0

    transport_out = state.get("selected_transport_outbound")
    transport_ret = state.get("selected_transport_return")
    if transport_out and transport_ret:
        actual_spending += transport_out.price + transport_ret.price

    stay = state.get("selected_stay")
    if stay:
        actual_spending += stay.total_price

    itinerary = state.get("itinerary")
    if itinerary:
        actual_spending += itinerary.total_cost

    if budget.total > 0:
        return ((actual_spending - budget.total) / budget.total) * 100
    return 0.0
