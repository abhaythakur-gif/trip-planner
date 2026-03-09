"""
Conversation Manager Agent.
Orchestrates conversational flow and extracts trip information from user messages.
"""

from typing import Tuple

from langchain_core.messages import SystemMessage, HumanMessage

from ..base_agent import BaseAgent
from ...schemas.conversation import RequiredTripFields, ConversationHistory
from ...schemas.state import TravelState
from ...llm.client import get_llm
from .tool import parse_extraction_response, merge_fields, generate_acknowledgment

_EXTRACTION_SYSTEM_PROMPT = """You are an information extraction specialist for travel planning.
Extract trip-related information from the user's message and return ONLY the extracted values.

Extract these fields (leave as NONE if not mentioned):
- destination: City/country name (e.g., "Paris", "France", "Tokyo")
- origin: Starting city/location
- start_date: Date in YYYY-MM-DD format OR relative terms (e.g., "next month", "in May")
- end_date: End date
- duration_days: Number of days (extract from phrases like "5 days", "a week", "weekend")
- budget: Dollar amount (extract numbers from "$2000", "2000 dollars", "around 2k")
- travelers: Number of people (extract from "2 people", "family of 4", "solo")
- preferences: Any preferences (food, activities, accommodation, travel style, etc.)

IMPORTANT:
- Extract ONLY what is explicitly mentioned
- Do not infer or assume
- Keep values concise

Return in this EXACT format (use NONE for missing values):
destination: value or NONE
origin: value or NONE
start_date: value or NONE
end_date: value or NONE
duration_days: value or NONE
budget: value or NONE
travelers: value or NONE
preferences: value or NONE
"""


class ConversationManagerAgent(BaseAgent):
    """
    Main conversation orchestrator that extracts information from user messages
    and updates accumulated context.
    """

    def __init__(self):
        super().__init__(name="ConversationManager")
        self.llm = get_llm()

    async def execute(self, state: TravelState) -> TravelState:
        """Process user message and update accumulated trip info."""

        self.logger.info("Starting conversation manager execution")

        user_message = None
        for msg in reversed(state.get("messages", [])):
            if msg.get("role") == "user":
                user_message = msg.get("content")
                break

        if not user_message:
            self.logger.warning("No user message found in state")
            return state

        self.logger.info(f"Processing user message: {user_message[:100]}...")

        conv_history = ConversationHistory(messages=list(state.get("messages", [])))
        current_fields = state.get("accumulated_trip_info") or RequiredTripFields()

        try:
            updated_fields, acknowledgment = await self.process(
                user_message, current_fields, conv_history
            )
        except Exception as e:
            self.logger.error(f"Error processing message: {type(e).__name__}: {e}")
            return state

        state["accumulated_trip_info"] = updated_fields

        if acknowledgment and acknowledgment != "Got it!":
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({"role": "assistant", "content": acknowledgment})

        self.logger.info("Conversation manager execution completed")
        return state

    async def process(
        self,
        user_message: str,
        current_fields: RequiredTripFields,
        conversation_history: ConversationHistory,
    ) -> Tuple[RequiredTripFields, str]:
        """Extract info from user message and return updated fields + acknowledgment."""

        extracted = await self._extract_information(
            user_message, current_fields, conversation_history
        )
        updated_fields = merge_fields(current_fields, extracted)
        acknowledgment = generate_acknowledgment(extracted)
        return updated_fields, acknowledgment

    async def _extract_information(
        self,
        message: str,
        current_fields: RequiredTripFields,
        history: ConversationHistory,
    ) -> dict:
        """Call LLM to extract structured fields from the user's message."""

        context_info = (
            f"Current accumulated information:\n"
            f"- destination: {current_fields.destination or 'unknown'}\n"
            f"- origin: {current_fields.origin or 'unknown'}\n"
            f"- start_date: {current_fields.start_date or 'unknown'}\n"
            f"- duration: {current_fields.duration_days or current_fields.end_date or 'unknown'}\n"
            f"- budget: {current_fields.budget or 'unknown'}\n"
            f"- travelers: {current_fields.travelers}\n"
        )

        last_assistant = "Initial greeting"
        if len(history.messages) >= 2 and history.messages[-2].role == "assistant":
            last_assistant = history.messages[-2].content

        user_prompt = (
            f"{context_info}\n"
            f"Last assistant question (for context):\n{last_assistant}\n\n"
            f"User's response:\n{message}\n\n"
            "Extract NEW information from the user's response:"
        )

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            )
            return parse_extraction_response(response.content)
        except Exception as e:
            self.logger.error(f"Error extracting information: {type(e).__name__}: {e}")
            return {}
