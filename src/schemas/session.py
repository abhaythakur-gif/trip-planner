"""
Session state management for conversational flow.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

from .conversation import ConversationHistory, RequiredTripFields


class SessionState(BaseModel):
    """Manages conversation session state."""
    
    session_id: str = Field(description="Unique session identifier")
    phase: Literal["conversation", "planning", "completed"] = Field(
        default="conversation",
        description="Current phase of the session"
    )
    conversation_history: ConversationHistory = Field(default_factory=ConversationHistory)
    accumulated_context: RequiredTripFields = Field(default_factory=RequiredTripFields)
    information_complete: bool = Field(default=False)
    planning_triggered: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def update_timestamp(self):
        """Update the last modified timestamp."""
        self.updated_at = datetime.now()
    
    def add_user_message(self, content: str):
        """Add a user message and update timestamp."""
        self.conversation_history.add_message("user", content)
        self.update_timestamp()
    
    def add_assistant_message(self, content: str, metadata: Optional[dict] = None):
        """Add an assistant message and update timestamp."""
        self.conversation_history.add_message("assistant", content, metadata)
        self.update_timestamp()
    
    def transition_to_planning(self):
        """Transition from conversation to planning phase."""
        self.phase = "planning"
        self.planning_triggered = True
        self.update_timestamp()
    
    def complete_session(self):
        """Mark session as completed."""
        self.phase = "completed"
        self.update_timestamp()


class AccumulatedContext(BaseModel):
    """Tracks accumulated trip information across multiple conversation turns."""
    
    raw_user_inputs: list[str] = Field(
        default_factory=list,
        description="All raw user inputs"
    )
    extracted_entities: dict = Field(
        default_factory=dict,
        description="Extracted entities from conversation"
    )
    trip_fields: RequiredTripFields = Field(
        default_factory=RequiredTripFields,
        description="Structured trip information"
    )
    clarifications_needed: list[str] = Field(
        default_factory=list,
        description="Fields that need clarification"
    )
    
    def add_user_input(self, text: str):
        """Add raw user input."""
        self.raw_user_inputs.append(text)
    
    def update_field(self, field_name: str, value: any):
        """Update a specific trip field."""
        if hasattr(self.trip_fields, field_name):
            setattr(self.trip_fields, field_name, value)
    
    def get_completion_percentage(self) -> float:
        """Calculate how much information has been gathered."""
        total_fields = 6  # destination, origin, start_date, duration, budget, travelers
        filled_fields = 0
        
        if self.trip_fields.destination:
            filled_fields += 1
        if self.trip_fields.origin:
            filled_fields += 1
        if self.trip_fields.start_date:
            filled_fields += 1
        if self.trip_fields.end_date or self.trip_fields.duration_days:
            filled_fields += 1
        if self.trip_fields.budget:
            filled_fields += 1
        if self.trip_fields.travelers:
            filled_fields += 1
        
        return (filled_fields / total_fields) * 100
