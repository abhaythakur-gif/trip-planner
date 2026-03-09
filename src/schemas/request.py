"""
User request schemas - represents the structured input from natural language.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import date, datetime
from enum import Enum


class TravelStyle(str, Enum):
    """Travel style preferences."""
    LUXURY = "luxury"
    COMFORT = "comfort"
    BUDGET = "budget"
    BACKPACKER = "backpacker"
    ADVENTURE = "adventure"
    RELAXATION = "relaxation"
    CULTURAL = "cultural"
    FAMILY = "family"


class DateRange(BaseModel):
    """Date range for travel."""
    start: date
    end: date

    @field_validator("end")
    @classmethod
    def validate_end_after_start(cls, v, info):
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("End date must be after start date")
        return v

    @property
    def duration_days(self) -> int:
        """Calculate duration in days."""
        return (self.end - self.start).days


class TravelPreferences(BaseModel):
    """User preferences for the trip."""
    travel_style: List[TravelStyle] = Field(default_factory=list)
    accommodation_type: List[str] = Field(default_factory=lambda: ["hotel"])
    meal_preferences: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    pace: Optional[Literal["relaxed", "moderate", "packed"]] = None
    comfort_level: Optional[int] = None
    risk_tolerance: Optional[int] = None
    
    @field_validator("pace")
    @classmethod
    def validate_pace(cls, v):
        # Use default if None is provided
        if v is None:
            return "moderate"
        return v
    
    @field_validator("comfort_level")
    @classmethod
    def validate_comfort(cls, v):
        # Use default if None is provided
        if v is None:
            return 3
        if v < 1 or v > 5:
            raise ValueError("Comfort level must be between 1 and 5")
        return v
    
    @field_validator("risk_tolerance")
    @classmethod
    def validate_risk(cls, v):
        # Use default if None is provided
        if v is None:
            return 3
        if v < 1 or v > 5:
            raise ValueError("Risk tolerance must be between 1 and 5")
        return v


class TravelRequest(BaseModel):
    """Structured travel request extracted from natural language input."""
    
    # Core parameters
    destination: str = Field(..., description="Primary destination city/country")
    duration_days: Optional[int] = Field(default=None, description="Trip duration in days")
    budget_total: float = Field(..., gt=0, description="Total budget")
    currency: str = Field(default="USD", description="Currency code")
    
    # Dates
    travel_dates: Optional[DateRange] = Field(None, description="Specific travel dates")
    travel_month: Optional[str] = Field(None, description="Preferred month if dates flexible")
    
    # Travelers
    num_travelers: Optional[int] = Field(default=None, description="Number of travelers")
    
    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Duration must be greater than 0")
        return v
    
    @field_validator("num_travelers")
    @classmethod
    def validate_travelers(cls, v):
        # Use default if None is provided
        if v is None:
            return 1
        if v < 1:
            raise ValueError("Number of travelers must be at least 1")
        return v
    
    # Flexibility
    flexibility: bool = Field(default=False, description="Allow date/budget flexibility")
    date_flexibility_days: int = Field(default=0, ge=0, description="Days of flexibility for dates")
    budget_flexibility_percent: float = Field(default=0.0, ge=0, le=0.2, description="Budget flex up to 20%")
    
    # Preferences
    preferences: TravelPreferences = Field(default_factory=TravelPreferences)
    
    # Special requirements
    special_requirements: List[str] = Field(default_factory=list)
    
    # Origin (for transport search)
    origin: Optional[str] = Field(None, description="Starting city/airport")

    @field_validator("travel_month")
    @classmethod
    def validate_month(cls, v):
        if v:
            valid_months = [
                "january", "february", "march", "april", "may", "june",
                "july", "august", "september", "october", "november", "december"
            ]
            v_lower = v.lower()
            
            # Handle relative time expressions
            if any(rel in v_lower for rel in ["next", "this", "upcoming", "soon"]):
                # Accept relative time expressions as-is
                # The date conversion will happen in date_utils
                return v
            
            # Validate specific month names
            if v_lower not in valid_months:
                raise ValueError(f"Invalid month: {v}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        # Common currency codes
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR"]
        if v.upper() not in valid_currencies:
            raise ValueError(f"Currency {v} not supported")
        return v.upper()

    def get_date_range(self) -> Optional[DateRange]:
        """Get the date range for the trip."""
        return self.travel_dates

    def is_complete(self) -> bool:
        """Check if all required fields are present."""
        has_dates = self.travel_dates is not None or self.travel_month is not None
        has_origin = self.origin is not None
        return all([
            self.destination,
            self.duration_days,
            self.budget_total,
            has_dates,
            has_origin
        ])

    def missing_fields(self) -> List[str]:
        """Return list of missing required fields."""
        missing = []
        if not self.origin:
            missing.append("origin (starting city)")
        if not self.travel_dates and not self.travel_month:
            missing.append("travel_dates or travel_month")
        if not self.duration_days:
            missing.append("duration_days")
        return missing
    
    @property
    def start_date(self) -> Optional[date]:
        """Get the start date of the trip."""
        if self.travel_dates:
            return self.travel_dates.start
        return None
    
    @property
    def end_date(self) -> Optional[date]:
        """Get the end date of the trip."""
        if self.travel_dates:
            return self.travel_dates.end
        return None


class ClarificationRequest(BaseModel):
    """Request for clarification from user."""
    missing_fields: List[str]
    questions: List[str]
    partial_request: TravelRequest
