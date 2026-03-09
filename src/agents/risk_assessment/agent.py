"""
Risk Assessment Agent - assesses risks and calculates confidence.
"""

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.output import RiskSummary
from ...config import settings
from .tool import (
    identify_risk_scenarios,
    calculate_contingency_budget,
    generate_recommendations,
    calculate_overall_risk,
    calculate_confidence_score,
    generate_confidence_explanation,
)


class RiskAssessmentAgent(BaseAgent):
    """
    Assesses risks and calculates confidence score.

    Responsibilities:
    - Identify potential risks (weather, transport delays, budget overruns)
    - Simulate risk scenarios and their impacts
    - Calculate overall confidence score
    - Suggest contingency plans and fallback options
    - Estimate contingency budget needed
    """

    def __init__(self):
        super().__init__("risk_assessment")

    async def execute(self, state: TravelState) -> TravelState:
        """Assess risks and calculate confidence."""

        self.logger.info("Starting risk assessment")
        self.logger.debug(f"State keys available: {list(state.keys())}")

        # Identify risk scenarios
        self.logger.debug("Identifying risk scenarios")
        scenarios = identify_risk_scenarios(state, self.logger)
        self.logger.info(f"Identified {len(scenarios)} risk scenarios")

        # Calculate contingency budget
        self.logger.debug("Calculating contingency budget")
        contingency_budget = calculate_contingency_budget(scenarios)
        self.logger.debug(f"Contingency budget needed: ${contingency_budget:.2f}")

        # Generate recommendations
        self.logger.debug("Generating risk mitigation recommendations")
        recommendations = generate_recommendations(scenarios)
        self.logger.debug(f"Generated {len(recommendations)} recommendations")

        # Calculate overall risk score
        self.logger.debug("Calculating overall risk score")
        overall_risk = calculate_overall_risk(scenarios)
        self.logger.info(f"Overall risk score: {overall_risk:.1f}/100")

        # Create risk summary
        risk_summary = RiskSummary(
            overall_risk_score=overall_risk,
            scenarios=scenarios,
            contingency_budget_needed=contingency_budget,
            recommendations=recommendations,
        )

        state["risk_assessment"] = risk_summary

        # Calculate confidence score
        self.logger.debug("Calculating confidence score")
        confidence_score = calculate_confidence_score(state, overall_risk)
        confidence_explanation = generate_confidence_explanation(state, scenarios)
        self.logger.info(f"Confidence score: {confidence_score:.1f}/100")

        state["confidence_score"] = confidence_score
        state["confidence_explanation"] = confidence_explanation

        self.log_decision(
            state,
            decision=f"Risk assessment complete: {len(scenarios)} scenarios identified",
            reasoning=f"Confidence: {confidence_score:.1f}/100, Risk: {overall_risk:.1f}/100",
            alternatives=0,
        )

        self.logger.info(
            f"Risk assessment: {len(scenarios)} scenarios, confidence {confidence_score:.1f}%"
        )

        return state
