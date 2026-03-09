"""
Tool functions for the Risk Assessment Agent.
Standalone functions for risk scenario detection, scoring, and confidence calculation.
"""

from typing import List


def identify_risk_scenarios(state: dict, logger=None) -> list:
    """
    Detect potential risk scenarios from the current plan state.

    Returns:
        List of RiskScenario objects.
    """
    from ...schemas.output import RiskScenario

    scenarios = []

    if logger:
        logger.debug("Analyzing state for risk scenarios")

    # Weather risks
    weather = state.get("weather_data")
    if weather:
        if logger:
            logger.debug(
                f"Checking weather risks: overall_risk={weather.risk_assessment.overall_risk}"
            )
        if weather.risk_assessment.overall_risk in ["medium", "high"]:
            scenario = RiskScenario(
                scenario_type="weather_disruption",
                probability=0.3 if weather.risk_assessment.overall_risk == "medium" else 0.6,
                impact_severity=weather.risk_assessment.overall_risk,
                affected_components=["outdoor_activities", "transport"],
                fallback_recommendation="Reschedule outdoor activities to indoor alternatives",
                estimated_additional_cost=50.0,
            )
            scenarios.append(scenario)

    # Transport delay risks
    transport_out = state.get("selected_transport_outbound")
    if transport_out:
        scenario = RiskScenario(
            scenario_type="transport_delay",
            probability=0.2,
            impact_severity="medium",
            affected_components=["schedule", "first_day_activities"],
            fallback_recommendation="Keep first day schedule flexible",
            estimated_additional_cost=100.0,
        )
        scenarios.append(scenario)

    # Budget overrun risks
    optimization = state.get("optimization_results")
    if optimization and abs(optimization.budget_deviation) > 5:
        scenario = RiskScenario(
            scenario_type="budget_overrun",
            probability=0.4,
            impact_severity="medium" if optimization.budget_deviation < 15 else "high",
            affected_components=["budget", "activities"],
            fallback_recommendation="Prioritize free/low-cost activities",
            estimated_additional_cost=abs(optimization.budget_deviation * 10),
        )
        scenarios.append(scenario)

    # Accommodation risks
    stay = state.get("selected_stay")
    if stay and stay.cancellation_policy == "non-refundable":
        scenario = RiskScenario(
            scenario_type="accommodation_cancellation",
            probability=0.1,
            impact_severity="high",
            affected_components=["accommodation", "budget"],
            fallback_recommendation="Purchase travel insurance",
            estimated_additional_cost=stay.total_price,
        )
        scenarios.append(scenario)

    # Attraction booking risks
    attractions_list = state.get("attractions")
    if attractions_list:
        booking_required = [a for a in attractions_list.all_attractions if a.requires_booking]
        if len(booking_required) > 2:
            scenario = RiskScenario(
                scenario_type="attraction_unavailable",
                probability=0.25,
                impact_severity="low",
                affected_components=["activities", "schedule"],
                fallback_recommendation="Book popular attractions in advance, have backup options",
                estimated_additional_cost=20.0,
            )
            scenarios.append(scenario)

    return scenarios


def calculate_contingency_budget(scenarios: list) -> float:
    """Return recommended contingency budget based on probability-weighted risk costs."""
    severity_weight = {"low": 0.3, "medium": 0.5, "high": 0.8}
    total = 0.0
    for scenario in scenarios:
        weight = severity_weight.get(scenario.impact_severity, 0.5)
        total += scenario.estimated_additional_cost * scenario.probability * weight
    return total


def generate_recommendations(scenarios: list) -> List[str]:
    """Generate deduplicated risk mitigation recommendations."""
    recommendations = []
    for scenario in scenarios:
        if scenario.fallback_recommendation not in recommendations:
            recommendations.append(scenario.fallback_recommendation)

    if len(scenarios) >= 3:
        recommendations.append("Consider purchasing comprehensive travel insurance")

    recommendations.append("Keep emergency funds accessible")
    recommendations.append("Save important contact numbers and addresses offline")

    return recommendations


def calculate_overall_risk(scenarios: list) -> float:
    """Compute overall risk score 0–100 (higher = more risk)."""
    if not scenarios:
        return 10.0

    severity_scores = {"low": 30, "medium": 60, "high": 90}
    weighted_risks = [
        severity_scores.get(s.impact_severity, 50) * s.probability for s in scenarios
    ]
    overall_risk = sum(weighted_risks) / len(weighted_risks)
    return min(75.0, overall_risk)


def calculate_confidence_score(state: dict, overall_risk: float) -> float:
    """Compute plan confidence score 0–100 (higher = more confident)."""
    base_confidence = 100 - overall_risk

    optimization = state.get("optimization_results")
    if optimization:
        completeness_factor = optimization.data_completeness_score / 100
        base_confidence *= completeness_factor

    if optimization and not optimization.passed:
        base_confidence -= len(optimization.issues) * 5

    errors = state.get("errors", [])
    base_confidence -= len(errors) * 10

    return max(0.0, min(100.0, base_confidence))


def generate_confidence_explanation(state: dict, scenarios: list) -> str:
    """Return a human-readable explanation of the confidence score drivers."""
    parts = []

    high_risk = [s for s in scenarios if s.impact_severity == "high"]
    if high_risk:
        parts.append(f"{len(high_risk)} high-risk scenarios identified")
    else:
        parts.append("No critical risks identified")

    optimization = state.get("optimization_results")
    if optimization:
        if optimization.data_completeness_score >= 90:
            parts.append("all data complete")
        elif optimization.data_completeness_score >= 70:
            parts.append("most data complete")
        else:
            parts.append("some data missing")

        if abs(optimization.budget_deviation) < 5:
            parts.append("budget well-managed")
        elif abs(optimization.budget_deviation) < 15:
            parts.append("budget slightly stretched")
        else:
            parts.append("budget concerns")

    return "; ".join(parts).capitalize()
