"""
Constraint schemas - represents hard and soft constraints for planning.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date, time


class HardConstraints(BaseModel):
    """Non-negotiable constraints that must be satisfied."""
    
    # Budget constraints
    max_budget: float = Field(..., gt=0, description="Absolute maximum budget")
    min_budget_buffer: float = Field(default=0.05, ge=0, le=0.2, description="Minimum buffer percentage")
    
    # Time constraints
    duration_days: int = Field(..., gt=0, description="Fixed trip duration")
    date_start: date = Field(..., description="Trip start date")
    date_end: date = Field(..., description="Trip end date")
    
    # Travel constraints
    max_flight_duration_hours: Optional[int] = Field(None, ge=0, description="Maximum flight duration")
    max_connections: Optional[int] = Field(None, ge=0, description="Maximum number of connections")
    
    # Legal constraints
    visa_required: bool = Field(default=False, description="Whether visa is required")
    passport_valid: bool = Field(default=True, description="Whether passport is valid")

    @property
    def min_buffer_amount(self) -> float:
        """Calculate minimum buffer amount in currency."""
        return self.max_budget * self.min_budget_buffer

    @property
    def max_spendable(self) -> float:
        """Maximum amount that can be spent (budget - min buffer)."""
        return self.max_budget - self.min_buffer_amount


class SoftConstraints(BaseModel):
    """Preferences that can be relaxed if necessary."""
    
    # Comfort preferences
    comfort_level: int = Field(default=3, ge=1, le=5, description="1=budget, 5=luxury")
    risk_tolerance: int = Field(default=3, ge=1, le=5, description="1=risk-averse, 5=adventurous")
    
    # Pace preferences
    pace: Literal["relaxed", "moderate", "packed"] = Field(default="moderate")
    max_activities_per_day: int = Field(default=4, ge=1, le=8)
    min_rest_time_hours: float = Field(default=1.0, ge=0, le=4)
    
    # Accommodation preferences
    accommodation_types: List[str] = Field(default_factory=lambda: ["hotel"])
    min_hotel_rating: float = Field(default=3.0, ge=1, le=5, description="Minimum hotel rating")
    preferred_amenities: List[str] = Field(default_factory=list)
    
    # Meal preferences
    meal_preferences: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    
    # Activity preferences
    interests: List[str] = Field(default_factory=list)
    avoid_activities: List[str] = Field(default_factory=list)
    
    # Travel preferences
    preferred_airlines: List[str] = Field(default_factory=list)
    avoid_airlines: List[str] = Field(default_factory=list)
    preferred_departure_time: Optional[time] = None
    preferred_return_time: Optional[time] = None
    
    # Weather preferences
    min_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    avoid_rain: bool = Field(default=False)

    def relax_constraints(self, level: int = 1) -> 'SoftConstraints':
        """
        Relax constraints for replanning.
        
        Args:
            level: Relaxation level (1-3)
        
        Returns:
            New SoftConstraints with relaxed values
        """
        relaxed = self.model_copy()
        
        if level >= 1:
            # Level 1: Relax rating requirements
            relaxed.min_hotel_rating = max(2.5, self.min_hotel_rating - 0.5)
            relaxed.max_activities_per_day += 1
        
        if level >= 2:
            # Level 2: Relax comfort level
            relaxed.comfort_level = max(1, self.comfort_level - 1)
            relaxed.min_hotel_rating = max(2.0, self.min_hotel_rating - 1.0)
        
        if level >= 3:
            # Level 3: Significant relaxation
            relaxed.preferred_amenities = []
            relaxed.preferred_airlines = []
            relaxed.avoid_rain = False
        
        return relaxed


class ConstraintSet(BaseModel):
    """Complete set of constraints for trip planning."""
    
    hard: HardConstraints
    soft: SoftConstraints
    
    # Flexibility flags
    allow_budget_flex: bool = Field(default=False)
    allow_date_flex: bool = Field(default=False)
    
    # Violation tracking
    violations: List[str] = Field(default_factory=list)
    
    def add_violation(self, violation: str) -> None:
        """Record a constraint violation."""
        if violation not in self.violations:
            self.violations.append(violation)
    
    def has_violations(self) -> bool:
        """Check if any constraints have been violated."""
        return len(self.violations) > 0
    
    def clear_violations(self) -> None:
        """Clear all recorded violations."""
        self.violations = []
