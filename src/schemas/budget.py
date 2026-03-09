"""
Budget allocation schema - represents how budget is divided among categories.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional


class BudgetAllocation(BaseModel):
    """Budget allocation across travel categories."""
    
    total: float = Field(..., gt=0, description="Total available budget")
    currency: str = Field(default="USD")
    
    # Category allocations
    transport: float = Field(..., ge=0, description="Allocated for flights/transport")
    stay: float = Field(..., ge=0, description="Allocated for accommodation")
    food: float = Field(..., ge=0, description="Allocated for meals")
    activities: float = Field(..., ge=0, description="Allocated for attractions/activities")
    buffer: float = Field(..., ge=0, description="Emergency buffer")
    
    # Original allocations (for tracking adjustments)
    original_transport: Optional[float] = None
    original_stay: Optional[float] = None
    original_food: Optional[float] = None
    original_activities: Optional[float] = None
    original_buffer: Optional[float] = None
    
    # Actual spending
    spent_transport: float = Field(default=0.0, ge=0)
    spent_stay: float = Field(default=0.0, ge=0)
    spent_food: float = Field(default=0.0, ge=0)
    spent_activities: float = Field(default=0.0, ge=0)
    
    @field_validator("transport", "stay", "food", "activities", "buffer")
    @classmethod
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError("Budget allocations must be non-negative")
        return v
    
    def model_post_init(self, __context) -> None:
        """Store original allocations after initialization."""
        if self.original_transport is None:
            self.original_transport = self.transport
            self.original_stay = self.stay
            self.original_food = self.food
            self.original_activities = self.activities
            self.original_buffer = self.buffer
    
    @property
    def allocated_total(self) -> float:
        """Total allocated across all categories."""
        return self.transport + self.stay + self.food + self.activities + self.buffer
    
    @property
    def spent_total(self) -> float:
        """Total spent so far."""
        return self.spent_transport + self.spent_stay + self.spent_food + self.spent_activities
    
    @property
    def remaining(self) -> float:
        """Remaining budget."""
        return self.total - self.spent_total
    
    @property
    def remaining_buffer(self) -> float:
        """Remaining buffer amount."""
        return max(0, self.buffer - (self.spent_total - (self.transport + self.stay + self.food + self.activities)))
    
    def is_valid(self) -> bool:
        """Check if allocation is valid (sums to total)."""
        return abs(self.allocated_total - self.total) < 0.01  # Allow small floating point errors
    
    def get_remaining_by_category(self) -> Dict[str, float]:
        """Get remaining budget per category."""
        return {
            "transport": self.transport - self.spent_transport,
            "stay": self.stay - self.spent_stay,
            "food": self.food - self.spent_food,
            "activities": self.activities - self.spent_activities,
            "buffer": self.buffer
        }
    
    def allocate_spending(self, category: str, amount: float) -> None:
        """
        Record spending in a category.
        
        Args:
            category: Category name (transport, stay, food, activities)
            amount: Amount spent
        """
        if category == "transport":
            self.spent_transport += amount
        elif category == "stay":
            self.spent_stay += amount
        elif category == "food":
            self.spent_food += amount
        elif category == "activities":
            self.spent_activities += amount
        else:
            raise ValueError(f"Invalid category: {category}")
    
    def rebalance(self, overage: Dict[str, float]) -> bool:
        """
        Rebalance budget when a category exceeds allocation.
        
        Args:
            overage: Dictionary of category -> overage amount
        
        Returns:
            True if rebalancing successful, False otherwise
        """
        total_overage = sum(overage.values())
        
        # Can we cover from buffer?
        if total_overage <= self.buffer:
            self.buffer -= total_overage
            for category, amount in overage.items():
                if category == "transport":
                    self.transport += amount
                elif category == "stay":
                    self.stay += amount
                elif category == "food":
                    self.food += amount
                elif category == "activities":
                    self.activities += amount
            return True
        
        # Try to reallocate from activities (lowest priority)
        if overage.get("activities", 0) == 0 and self.activities > total_overage:
            self.activities -= total_overage
            for category, amount in overage.items():
                if category == "transport":
                    self.transport += amount
                elif category == "stay":
                    self.stay += amount
                elif category == "food":
                    self.food += amount
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary of allocations."""
        return {
            "transport": self.transport,
            "stay": self.stay,
            "food": self.food,
            "activities": self.activities,
            "buffer": self.buffer
        }
