"""
Information Completeness Checker Agent.
Validates whether all required trip information has been collected.
"""

from langchain_core.messages import SystemMessage, HumanMessage

from ..base_agent import BaseAgent
from ...schemas.conversation import RequiredTripFields, InformationCompleteness
from ...schemas.state import TravelState
from ...llm.client import get_llm
from .tool import parse_llm_extraction


class InformationCheckerAgent(BaseAgent):
    """
    Agent that checks if all required information for trip planning has been collected.
    Returns what's missing and prioritises questions.
    """

    def __init__(self):
        super().__init__(name="InformationChecker")
        self.llm = get_llm()

    async def execute(self, state: TravelState) -> TravelState:
        """Validate completeness of trip information."""

        self.logger.info("Starting information completeness check")
        accumulated_fields = state.get("accumulated_trip_info") or RequiredTripFields()

        conv_context = "\n".join(
            [
                f"{msg['role']}: {msg['content']}"
                for msg in state.get("messages", [])[-10:]
            ]
        )

        completeness = await self.process(accumulated_fields, conv_context)

        self.logger.info(
            f"Information complete: {completeness.is_complete}, missing: {completeness.missing_fields}"
        )

        state["information_complete"] = completeness.is_complete
        state["missing_fields"] = completeness.missing_fields
        state["accumulated_trip_info"] = completeness.accumulated_info

        return state

    async def process(
        self,
        accumulated_fields: RequiredTripFields,
        conversation_context: str = "",
    ) -> InformationCompleteness:
        """Check completeness of trip information."""

        is_complete = accumulated_fields.is_complete()
        missing_fields = accumulated_fields.get_missing_fields()

        total_fields = 6
        filled_fields = total_fields - len(missing_fields)
        confidence = filled_fields / total_fields

        if is_complete:
            return InformationCompleteness(
                is_complete=True,
                missing_fields=[],
                accumulated_info=accumulated_fields,
                confidence_score=1.0,
                next_question=None,
            )

        # Attempt to recover missed info from conversation with LLM
        if conversation_context:
            updated = await self._llm_validate_fields(
                accumulated_fields, conversation_context, missing_fields
            )
            if updated:
                accumulated_fields = updated
                is_complete = accumulated_fields.is_complete()
                missing_fields = accumulated_fields.get_missing_fields()
                filled_fields = total_fields - len(missing_fields)
                confidence = filled_fields / total_fields

        return InformationCompleteness(
            is_complete=is_complete,
            missing_fields=missing_fields,
            accumulated_info=accumulated_fields,
            confidence_score=confidence,
            next_question=None,
        )

    async def _llm_validate_fields(
        self,
        fields: RequiredTripFields,
        context: str,
        missing_fields: list,
    ) -> RequiredTripFields:
        """Use LLM to extract any information missed by the structural check."""

        system_prompt = (
            "You are an information extraction assistant.\n"
            "Read the conversation and extract trip planning information that might have been "
            "mentioned but not yet captured.\n\n"
            "Extract ONLY information that is explicitly stated. Do not assume or infer.\n\n"
            "Return in this exact format (use NONE for missing values):\n"
            "destination: value or NONE\n"
            "origin: value or NONE\n"
            "start_date: value or NONE\n"
            "end_date: value or NONE\n"
            "duration_days: value or NONE\n"
            "budget: value or NONE\n"
            "travelers: value or NONE\n"
            "preferences: value or NONE"
        )

        user_prompt = (
            f"Current accumulated information:\n{fields.model_dump_json(indent=2)}\n\n"
            f"Conversation context:\n{context}\n\n"
            f"Missing fields: {', '.join(missing_fields)}\n\n"
            "Extract any information from the conversation that fills in the missing fields."
        )

        try:
            response = await self.llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
            return parse_llm_extraction(response.content, fields)
        except Exception as e:
            self.logger.error(f"LLM validation error: {type(e).__name__}: {e}")
            return fields
