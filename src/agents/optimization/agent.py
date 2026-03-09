"""
Optimization Agent - performs global optimization and validation.
"""

from typing import List

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.output import OptimizationResults
from ...config import settings
from .tool import validate_budget, validate_schedule, check_completeness, calculate_budget_deviation


class OptimizationAgent(BaseAgent):
    """
    Performs global optimization and validation.

    Responsibilities:
    - Validate budget consistency across all components
    - Check schedule feasibility (no overlaps, reasonable timing)
    - Ensure data completeness
    - Identify optimization opportunities
    - Validate constraints satisfaction
    """

    def __init__(self):
        super().__init__("optimization")

    async def execute(self, state: TravelState) -> TravelState:
        """Perform global optimization."""

        self.logger.info("Starting global optimization and validation")
        self.logger.debug(f"State keys available: {list(state.keys())}")

        issues = []
        warnings = []

        # Validate budget
        self.logger.debug("Validating budget consistency")
        budget_issues = validate_budget(state)
        issues.extend(budget_issues)
        self.logger.debug(f"Budget validation: {len(budget_issues)} issues found")

        # Validate schedule
        self.logger.debug("Validating schedule feasibility")
        schedule_issues = validate_schedule(state)
        issues.extend(schedule_issues)
        self.logger.debug(f"Schedule validation: {len(schedule_issues)} issues found")

        # Check data completeness
        self.logger.debug("Checking data completeness")
        completeness_score = check_completeness(state)
        self.logger.info(f"Data completeness score: {completeness_score:.1f}%")

        # Calculate budget deviation
        self.logger.debug("Calculating budget deviation")
        budget_deviation = calculate_budget_deviation(state)
        self.logger.debug(f"Budget deviation: {budget_deviation:.1f}%")

        # Create optimization results
        optimization_results = OptimizationResults(
            passed=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            budget_deviation=budget_deviation,
            schedule_issues=schedule_issues,
            data_completeness_score=completeness_score,
        )

        state["optimization_results"] = optimization_results

        self.log_decision(
            state,
            decision="Optimization complete" if optimization_results.passed else "Optimization found issues",
            reasoning=f"{len(issues)} issues, {len(warnings)} warnings, completeness: {completeness_score:.1f}%",
            alternatives=0,
        )

        self.logger.info(
            f"Optimization: {len(issues)} issues, completeness {completeness_score:.1f}%"
        )

        return state
