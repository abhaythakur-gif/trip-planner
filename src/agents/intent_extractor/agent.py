"""
Intent Extractor Agent - extracts structured travel request from natural language.
"""

import json

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import ValidationError

from ..base_agent import BaseAgent
from ...schemas.state import TravelState
from ...schemas.request import TravelRequest, ClarificationRequest
from ...llm.client import get_llm
from ..prompts.intent_extractor import get_intent_extraction_prompt
from .tool import generate_clarification_questions


class IntentExtractorAgent(BaseAgent):
    """
    Extracts structured travel parameters from natural language input.

    Responsibilities:
    - Parse user query
    - Extract destination, duration, budget, dates, preferences
    - Validate completeness
    - Request clarification if needed
    """

    def __init__(self):
        super().__init__("intent_extractor")
        self.llm = get_llm()

    async def execute(self, state: TravelState) -> TravelState:
        """Extract structured request from natural language query."""

        query = state["raw_query"]
        self.logger.info(f"Starting intent extraction from query: {query[:100]}...")

        prompt = get_intent_extraction_prompt(query)
        messages = [
            SystemMessage(
                content="You are an expert travel planning assistant that extracts structured information from user queries."
            ),
            HumanMessage(content=prompt),
        ]

        self.logger.info(f"Calling LLM for intent extraction")
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content
        except Exception as llm_error:
            self.logger.error(f"LLM call failed: {type(llm_error).__name__}: {llm_error}")
            state["errors"].append(f"Intent extraction LLM call failed: {llm_error}")
            state["requires_clarification"] = True
            return state

        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                lines = cleaned_text.split("\n")[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_text = "\n".join(lines).strip()

            data = json.loads(cleaned_text)
            travel_request = TravelRequest(**data)

            if not travel_request.is_complete():
                missing = travel_request.missing_fields()
                questions = generate_clarification_questions(missing)
                clarification = ClarificationRequest(
                    missing_fields=missing,
                    questions=questions,
                    partial_request=travel_request,
                )
                state["clarification"] = clarification
                state["requires_clarification"] = True
                state["structured_request"] = travel_request
                self.log_decision(
                    state,
                    decision="Request clarification from user",
                    reasoning=f"Missing required fields: {', '.join(missing)}",
                    alternatives=0,
                )
            else:
                state["structured_request"] = travel_request
                state["requires_clarification"] = False
                self.log_decision(
                    state,
                    decision=f"Extracted complete travel request to {travel_request.destination}",
                    reasoning="All required fields present in user query",
                    alternatives=1,
                )
                self.logger.info("Successfully extracted complete travel request")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            state["errors"].append(f"Intent extraction JSON parse failed: {e}")
            state["requires_clarification"] = True
        except ValidationError as e:
            self.logger.error(f"Pydantic validation failed: {e}")
            state["errors"].append(f"Intent extraction validation failed: {e}")
            state["requires_clarification"] = True
        except Exception as e:
            self.logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            state["errors"].append(f"Intent extraction unexpected error: {e}")
            state["requires_clarification"] = True

        return state
