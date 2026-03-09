"""
Constraint Modeler Agent - converts travel request into hard and soft constraints.
"""

import json
from datetime import date

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.constraints import ConstraintSet, HardConstraints, SoftConstraints
from ...utils.prompts import get_constraint_modeling_prompt
from ...utils.date_utils import parse_month_to_date_range, get_date_range
from ...config import settings
from .tool import infer_min_rating, infer_max_activities


class ConstraintModelerAgent(BaseAgent):
    """
    Models hard and soft constraints from travel request.

    Responsibilities:
    - Define absolute constraints (budget max, dates, duration)
    - Define preferences (comfort, pace, accommodation)
    - Set constraint flexibility levels
    """

    def __init__(self):
        super().__init__("constraint_modeler")

        # Initialize LLM
        if settings.llm_provider == "openai":
            self.llm = ChatOpenAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                api_key=settings.openai_api_key,
            )
        else:
            self.llm = ChatAnthropic(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                api_key=settings.anthropic_api_key,
            )

    async def execute(self, state: TravelState) -> TravelState:
        """Model constraints from travel request."""

        self.logger.info("Starting constraint modeling")
        request = state["structured_request"]
        if not request:
            self.logger.error("No structured request available in state")
            self.logger.debug(f"State keys: {list(state.keys())}")
            return state

        self.logger.info(f"Modeling constraints for destination: {request.destination}")
        self.logger.debug(
            f"Request details: budget=${request.budget_total}, "
            f"duration={request.duration_days} days, travelers={request.num_travelers}"
        )

        # Determine dates
        self.logger.debug("Determining travel dates")
        if request.travel_dates:
            start_date = request.travel_dates.start
            end_date = request.travel_dates.end
            self.logger.info(f"Using provided travel dates: {start_date} to {end_date}")
        elif request.travel_month:
            self.logger.debug(f"Inferring dates from travel month: {request.travel_month}")
            try:
                start_date, _ = parse_month_to_date_range(request.travel_month)
                _, end_date = get_date_range(start_date, request.duration_days)
                self.logger.info(f"Successfully inferred dates from month: {start_date} to {end_date}")
                from ...schemas.request import DateRange
                request.travel_dates = DateRange(start=start_date, end=end_date)
                state["structured_request"] = request
                self.logger.debug("Updated structured_request with inferred dates")
            except Exception as e:
                self.logger.error(
                    f"Failed to parse travel month '{request.travel_month}': {type(e).__name__}: {str(e)}"
                )
                request.travel_dates = None

        if not request.travel_dates:
            self.logger.warning("No travel dates or month provided, using default dates")
            from datetime import timedelta
            start_date = date.today() + timedelta(days=30)
            _, end_date = get_date_range(start_date, request.duration_days)
            self.logger.warning(f"Using default dates (30 days from today): {start_date} to {end_date}")
            from ...schemas.request import DateRange
            request.travel_dates = DateRange(start=start_date, end=end_date)
            state["structured_request"] = request
            self.logger.debug("Updated structured_request with default dates")
        else:
            start_date = request.travel_dates.start
            end_date = request.travel_dates.end

        # Build hard constraints
        self.logger.debug("Building hard constraints")
        try:
            hard = HardConstraints(
                max_budget=request.budget_total,
                min_budget_buffer=settings.min_buffer_percentage,
                duration_days=request.duration_days,
                date_start=start_date,
                date_end=end_date,
                max_flight_duration_hours=24,
                max_connections=2,
            )
            self.logger.info(
                f"Hard constraints created: max_budget=${hard.max_budget}, "
                f"duration={hard.duration_days} days, buffer>={hard.min_budget_buffer * 100}%"
            )
        except Exception as e:
            self.logger.error(f"Failed to create HardConstraints: {type(e).__name__}: {str(e)}")
            raise

        # Build soft constraints from preferences
        self.logger.debug("Building soft constraints from preferences")
        try:
            prefs = request.preferences
            self.logger.debug(
                f"Preferences: comfort={prefs.comfort_level}, risk={prefs.risk_tolerance}, pace={prefs.pace}"
            )

            min_rating = infer_min_rating(prefs.comfort_level)
            max_activities = infer_max_activities(prefs.pace)
            self.logger.debug(
                f"Inferred: min_hotel_rating={min_rating}, max_activities_per_day={max_activities}"
            )

            soft = SoftConstraints(
                comfort_level=prefs.comfort_level,
                risk_tolerance=prefs.risk_tolerance,
                pace=prefs.pace,
                accommodation_types=prefs.accommodation_type,
                meal_preferences=prefs.meal_preferences,
                interests=prefs.interests,
                min_hotel_rating=min_rating,
                max_activities_per_day=max_activities,
            )
            self.logger.info(
                f"Soft constraints created: comfort={soft.comfort_level}/5, "
                f"pace={soft.pace}, min_rating={soft.min_hotel_rating}"
            )
        except Exception as e:
            self.logger.error(f"Failed to create SoftConstraints: {type(e).__name__}: {str(e)}")
            raise

        # Create constraint set
        self.logger.debug("Creating constraint set with flexibility options")
        try:
            allow_budget_flex = request.flexibility and request.budget_flexibility_percent > 0
            allow_date_flex = request.flexibility and request.date_flexibility_days > 0
            self.logger.debug(f"Flexibility: budget={allow_budget_flex}, dates={allow_date_flex}")

            constraints = ConstraintSet(
                hard=hard,
                soft=soft,
                allow_budget_flex=allow_budget_flex,
                allow_date_flex=allow_date_flex,
            )

            state["constraints"] = constraints
            self.logger.info("Constraint set successfully created and stored in state")
        except Exception as e:
            self.logger.error(f"Failed to create ConstraintSet: {type(e).__name__}: {str(e)}")
            raise

        self.log_decision(
            state,
            decision=f"Modeled constraints: budget ${hard.max_budget}, {hard.duration_days} days",
            reasoning=(
                f"Based on {request.destination.lower()} and "
                f"{request.preferences.comfort_level}/5 comfort level"
            ),
            alternatives=1,
        )

        self.logger.info("Constraint modeling completed successfully")

        return state
