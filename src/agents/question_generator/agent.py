"""
Question Generator Agent.
Generates contextual follow-up questions to gather missing trip information.
"""

from typing import List

from langchain_core.messages import SystemMessage, HumanMessage

from ..base_agent import BaseAgent
from ...schemas.conversation import RequiredTripFields
from ...schemas.state import TravelState
from ...llm.client import get_llm
from .tool import get_next_priority_field, get_template_question

_SYSTEM_PROMPT = """You are a friendly travel planning assistant.
Your job is to ask ONE natural, conversational question to gather missing trip information.

Guidelines:
- Be warm and friendly
- Reference previously gathered information when relevant
- Keep questions concise and clear
- Don't ask multiple questions at once
- Use natural language, not form-like prompts
- Show enthusiasm about their trip

Examples:
- "Where would you like to go?" (for destination)
- "When are you planning to start your trip?" (for start_date)
- "How many days would you like to stay?" (for duration)
- "What's your approximate budget for this trip?" (for budget)
- "Which city will you be traveling from?" (for origin)
"""


class QuestionGeneratorAgent(BaseAgent):
    """
    Agent that generates natural, contextual follow-up questions
    to gather missing trip planning information.
    """

    def __init__(self):
        super().__init__(name="QuestionGenerator")
        self.llm = get_llm()

    async def execute(self, state: TravelState) -> TravelState:
        """Generate next follow-up question and add it to state messages."""

        self.logger.info("Starting question generation")
        missing_fields = state.get("missing_fields", [])
        accumulated_fields = state.get("accumulated_trip_info") or RequiredTripFields()

        conv_history = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in state.get("messages", [])[-5:]]
        )

        try:
            question = await self.process(missing_fields, accumulated_fields, conv_history)
        except Exception as e:
            self.logger.error(f"Error generating question: {type(e).__name__}: {e}")
            question = "Could you tell me more about your travel plans?"

        state["next_question"] = question
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({"role": "assistant", "content": question})

        self.logger.info(f"Generated question: {question}")
        return state

    async def process(
        self,
        missing_fields: List[str],
        accumulated_fields: RequiredTripFields,
        conversation_history: str = "",
    ) -> str:
        """Generate a natural follow-up question for the next missing field."""

        if not missing_fields:
            return "Great! I have all the information I need. Let me start planning your trip!"

        next_field = get_next_priority_field(missing_fields)
        return await self._generate_contextual_question(
            next_field, accumulated_fields, conversation_history
        )

    async def _generate_contextual_question(
        self,
        field: str,
        accumulated_fields: RequiredTripFields,
        conversation_history: str,
    ) -> str:
        """Generate a contextual question using LLM, with template fallback."""

        known_parts = []
        if accumulated_fields.destination:
            known_parts.append(f"destination: {accumulated_fields.destination}")
        if accumulated_fields.start_date:
            known_parts.append(f"start date: {accumulated_fields.start_date}")
        if accumulated_fields.duration_days:
            known_parts.append(f"duration: {accumulated_fields.duration_days} days")
        if accumulated_fields.budget:
            known_parts.append(f"budget: ${accumulated_fields.budget}")
        if accumulated_fields.origin:
            known_parts.append(f"origin: {accumulated_fields.origin}")

        known_info = ", ".join(known_parts) if known_parts else "nothing yet"
        recent_history = conversation_history[-500:] if conversation_history else "Just started"

        user_prompt = (
            f"We need to ask about: {field}\n\n"
            f"What we already know: {known_info}\n\n"
            f"Recent conversation:\n{recent_history}\n\n"
            f"Generate ONE friendly question to ask about the {field}.\n"
            "Return ONLY the question, nothing else."
        )

        try:
            response = await self.llm.ainvoke(
                [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
            )
            question = response.content.strip().strip('"').strip("'")
            if not question.endswith("?"):
                question += "?"
            return question
        except Exception as e:
            self.logger.error(f"LLM question generation failed: {type(e).__name__}: {e}")
            return get_template_question(field, accumulated_fields)
