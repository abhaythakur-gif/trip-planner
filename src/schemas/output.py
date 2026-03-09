"""
Output schema - represents the final travel plan output.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from .agent_outputs import (
    TransportOption, StayOption, MultiDayItinerary
)
from .budget import BudgetAllocation


class Decision(BaseModel):
    """A decision made during planning."""
    
    timestamp: datetime
    component: str = Field(..., description="Which agent/component made the decision")
    decision: str = Field(..., description="What was decided")
    reasoning: str = Field(..., description="Why this decision was made")
    alternatives_considered: int = Field(default=0, ge=0)


class RiskScenario(BaseModel):
    """A risk scenario simulation."""
    
    scenario_type: str = Field(..., description="weather, transport_delay, budget_overrun, etc.")
    probability: float = Field(..., ge=0, le=1)
    impact_severity: str = Field(..., description="low, medium, high")
    affected_components: List[str]
    fallback_recommendation: str
    estimated_additional_cost: float = Field(default=0.0, ge=0)


class RiskSummary(BaseModel):
    """Risk assessment summary."""
    
    overall_risk_score: float = Field(..., ge=0, le=100)
    scenarios: List[RiskScenario]
    contingency_budget_needed: float
    recommendations: List[str]


class FallbackOption(BaseModel):
    """A fallback/alternative option."""
    
    trigger: str = Field(..., description="What triggers this fallback")
    alternative: str = Field(..., description="The alternative action")
    additional_cost: float = Field(default=0.0)


class TripSummary(BaseModel):
    """High-level trip summary."""
    
    destination: str
    origin: str
    duration_days: int
    num_travelers: int
    
    departure_date: datetime
    return_date: datetime
    
    total_budget: float
    total_cost: float
    remaining_budget: float
    
    currency: str = "USD"


class OptimizationResults(BaseModel):
    """Results from global optimization pass."""
    
    passed: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    budget_deviation: float = Field(default=0.0)
    schedule_issues: List[str] = Field(default_factory=list)
    data_completeness_score: float = Field(default=100.0, ge=0, le=100)


class FinalTravelPlan(BaseModel):
    """The complete final travel plan."""
    
    # Summary
    summary: TripSummary
    budget_breakdown: Optional[BudgetAllocation] = None
    
    # Selected options (optional in case of incomplete plans)
    transport_outbound: Optional[TransportOption] = None
    transport_return: Optional[TransportOption] = None
    accommodation: Optional[StayOption] = None
    
    # Itinerary
    daily_itinerary: Optional[MultiDayItinerary] = None
    
    # Risk & confidence
    risk_summary: Optional[RiskSummary] = None
    fallback_options: List[FallbackOption] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0, le=100)
    confidence_explanation: str = ""
    
    # Reasoning
    decision_log: List[Decision] = Field(default_factory=list)
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)
    total_token_usage: int = Field(default=0, ge=0)
    replans_performed: int = Field(default=0, ge=0)
    execution_time_seconds: float = Field(default=0.0, ge=0)
    
    def to_markdown(self) -> str:
        """Convert plan to Markdown format."""
        md = f"""# 🌍 Your Travel Plan to {self.summary.destination}

**Dates**: {self.summary.departure_date.date()} to {self.summary.return_date.date()}
**Duration**: {self.summary.duration_days} days
**Travelers**: {self.summary.num_travelers}
**Confidence Score**: {self.confidence_score:.1f}/100 ⭐

---

## 💰 Budget Breakdown

"""
        if self.budget_breakdown:
            md += f"""| Category | Allocated | Spent | Remaining |
|----------|-----------|-------|-----------|
| Transport | ${self.budget_breakdown.transport:.2f} | ${self.budget_breakdown.spent_transport:.2f} | ${self.budget_breakdown.transport - self.budget_breakdown.spent_transport:.2f} |
| Stay | ${self.budget_breakdown.stay:.2f} | ${self.budget_breakdown.spent_stay:.2f} | ${self.budget_breakdown.stay - self.budget_breakdown.spent_stay:.2f} |
| Food | ${self.budget_breakdown.food:.2f} | ${self.budget_breakdown.spent_food:.2f} | ${self.budget_breakdown.food - self.budget_breakdown.spent_food:.2f} |
| Activities | ${self.budget_breakdown.activities:.2f} | ${self.budget_breakdown.spent_activities:.2f} | ${self.budget_breakdown.activities - self.budget_breakdown.spent_activities:.2f} |
| Buffer | ${self.budget_breakdown.buffer:.2f} | - | ${self.budget_breakdown.buffer:.2f} |
| **Total** | **${self.budget_breakdown.total:.2f}** | **${self.budget_breakdown.spent_total:.2f}** | **${self.budget_breakdown.remaining:.2f}** |

"""
        else:
            md += "_Budget information not available_\n\n"
        
        md += "---\n\n## ✈️ Travel Details\n\n"
        
        if self.transport_outbound:
            md += f"""### Outbound Flight
- **{self.transport_outbound.carrier}** {self.transport_outbound.flight_number or ''}
- Departs: {self.transport_outbound.origin} at {self.transport_outbound.departure.strftime('%H:%M')}
- Arrives: {self.transport_outbound.destination} at {self.transport_outbound.arrival.strftime('%H:%M')}
- Duration: {self.transport_outbound.duration_hours:.1f} hours
- Price: ${self.transport_outbound.price:.2f}

"""
        else:
            md += "### Outbound Flight\n_Not available_\n\n"
        
        if self.transport_return:
            md += f"""### Return Flight
- **{self.transport_return.carrier}** {self.transport_return.flight_number or ''}
- Departs: {self.transport_return.origin} at {self.transport_return.departure.strftime('%H:%M')}
- Arrives: {self.transport_return.destination} at {self.transport_return.arrival.strftime('%H:%M')}
- Duration: {self.transport_return.duration_hours:.1f} hours
- Price: ${self.transport_return.price:.2f}

"""
        else:
            md += "### Return Flight\n_Not available_\n\n"
        
        md += "---\n\n## 🏨 Accommodation\n\n"
        
        if self.accommodation:
            md += f"""**{self.accommodation.name}** ({self.accommodation.rating:.1f}⭐)
- Location: {self.accommodation.location.address}
- Price per night: ${self.accommodation.price_per_night:.2f}
- Total: ${self.accommodation.total_price:.2f}
- Distance to center: {self.accommodation.distance_to_center_km:.1f} km

"""
        else:
            md += "_Accommodation information not available_\n\n"
        
        md += "---\n\n## 📅 Day-by-Day Itinerary\n\n"
        
        if self.daily_itinerary and self.daily_itinerary.days:
            for day in self.daily_itinerary.days:
                md += f"""
### Day {day.day_number} - {day.date.strftime('%B %d, %Y')}
"""
                if day.weather:
                    md += f"**Weather**: {day.weather.condition} ({day.weather.temp_min:.0f}°C - {day.weather.temp_max:.0f}°C)\n\n"
                
                for activity in day.activities:
                    md += f"- **{activity.time_start.strftime('%H:%M')}** - {activity.attraction.name}\n"
                
                md += f"\n**Daily Cost**: ${day.total_cost:.2f}\n\n"
        else:
            md += "_Itinerary not available_\n\n"
        
        md += "\n---\n\n## ⚠️ Risk Assessment\n\n"
        
        if self.risk_summary:
            md += f"**Overall Risk**: {self.risk_summary.overall_risk_score:.1f}/100\n\n**Key Considerations**:\n"
            for rec in self.risk_summary.recommendations[:5]:
                md += f"- {rec}\n"
        else:
            md += "_Risk assessment not available_\n"
        
        md += "\n---\n\n## 🎯 Confidence & Reasoning\n\n"
        md += f"**Confidence Score**: {self.confidence_score:.1f}/100\n\n"
        md += f"{self.confidence_explanation}\n\n"
        
        return md
