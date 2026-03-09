"""
Conversation schemas for the conversational AI layer.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class ConversationMessage(BaseModel):
    """A single message in the conversation."""
    
    role: Literal["user", "assistant", "system"] = Field(
        description="Who sent the message"
    )
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class ConversationHistory(BaseModel):
    """Complete conversation history."""
    
    messages: List[ConversationMessage] = Field(default_factory=list)
    session_id: Optional[str] = Field(default=None)
    
    def add_message(self, role: str, content: str, metadata: Optional[dict] = None):
        """Add a message to history."""
        self.messages.append(
            ConversationMessage(role=role, content=content, metadata=metadata)
        )
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None
    
    def get_context_string(self, max_messages: int = 10) -> str:
        """Get conversation context as a string."""
        recent = self.messages[-max_messages:]
        return "\n".join([f"{msg.role}: {msg.content}" for msg in recent])


class RequiredTripFields(BaseModel):
    """Required fields for trip planning."""
    
    destination: Optional[str] = Field(default=None, description="Destination city/country")
    origin: Optional[str] = Field(default=None, description="Origin city")
    start_date: Optional[str] = Field(default=None, description="Trip start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="Trip end date (YYYY-MM-DD)")
    duration_days: Optional[int] = Field(default=None, description="Trip duration in days")
    budget: Optional[float] = Field(default=None, description="Total budget")
    travelers: int = Field(default=1, description="Number of travelers")
    preferences: Optional[str] = Field(default=None, description="User preferences")
    
    def is_complete(self) -> bool:
        """Check if all required fields are populated."""
        # Helper to check if value is truly present (not None or empty string)
        def is_present(val):
            if val is None or val == "":
                return False
            # For numeric fields, 0 is not valid
            if isinstance(val, (int, float)) and val <= 0:
                return False
            return True
        
        # Must have these fields
        required_present = all([
            is_present(self.destination),
            is_present(self.origin),
            is_present(self.start_date),
            is_present(self.budget),
        ])
        
        # Must have either end_date OR duration_days
        has_duration = is_present(self.end_date) or is_present(self.duration_days)
        
        return required_present and has_duration
    
    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields."""
        missing = []
        
        # Helper to check if value is missing
        def is_missing(val):
            if val is None or val == "":
                return True
            # For numeric fields, 0 or negative is not valid
            if isinstance(val, (int, float)) and val <= 0:
                return True
            return False
        
        if is_missing(self.destination):
            missing.append("destination")
        if is_missing(self.origin):
            missing.append("origin")
        if is_missing(self.start_date):
            missing.append("start_date")
        if is_missing(self.end_date) and is_missing(self.duration_days):
            missing.append("duration")
        if is_missing(self.budget):
            missing.append("budget")
        
        return missing
    
    def to_query_string(self) -> str:
        """Convert accumulated fields to a natural language query."""
        parts = []
        
        # Helper to check if value is valid (not None, not empty, not placeholder)
        def is_valid(val):
            if val is None or val == "":
                return False
            # Check for NONE placeholders (shouldn't happen, but be defensive)
            if isinstance(val, str) and val.strip().upper() in ("NONE", "[NONE]"):
                return False
            return True
        
        if is_valid(self.destination):
            parts.append(f"travel to {self.destination}")
        if is_valid(self.origin):
            parts.append(f"from {self.origin}")
        if is_valid(self.start_date):
            parts.append(f"starting {self.start_date}")
        if is_valid(self.duration_days):
            parts.append(f"for {self.duration_days} days")
        elif is_valid(self.end_date):
            parts.append(f"until {self.end_date}")
        if is_valid(self.budget):
            parts.append(f"with budget ${self.budget}")
        if self.travelers > 1:
            parts.append(f"for {self.travelers} travelers")
        if is_valid(self.preferences):
            parts.append(f"preferences: {self.preferences}")
        
        return ", ".join(parts) if parts else "a trip"


class InformationCompleteness(BaseModel):
    """Status of information completeness."""
    
    is_complete: bool = Field(description="Whether all required info is present")
    missing_fields: List[str] = Field(default_factory=list)
    accumulated_info: RequiredTripFields
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    next_question: Optional[str] = Field(default=None)
