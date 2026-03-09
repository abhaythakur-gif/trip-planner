"""
State schema - represents the complete shared state for the travel planning workflow.
This is used by LangGraph to manage state across all agents.
"""

from typing import TypedDict, Annotated, List, Optional
from operator import add
from datetime import datetime

from .request import TravelRequest, ClarificationRequest
from .constraints import ConstraintSet
from .budget import BudgetAllocation
from .agent_outputs import (
    TransportOption, StayOption, WeatherData,
    AttractionList, MultiDayItinerary
)
from .output import (
    OptimizationResults, RiskSummary, FinalTravelPlan, Decision
)
from .conversation import RequiredTripFields, ConversationHistory


class AuditEntry(TypedDict):
    """Single audit log entry."""
    timestamp: str
    node: str
    action: str
    success: bool
    duration_ms: Optional[float]
    token_usage: Optional[int]
    errors: Optional[List[str]]


class CalendarValidation(TypedDict):
    """Calendar validation results."""
    conflicts_found: bool
    conflicting_events: List[dict]
    alternative_windows: List[dict]
    validation_passed: bool


class TravelState(TypedDict):
    """
    Complete state for the travel planning workflow.
    Agents read and write to this shared state.
    """
    
    # Input & conversation
    raw_query: str
    messages: Annotated[List[dict], add]  # Conversation history
    
    # NEW: Conversational layer fields
    conversation_mode: bool  # True if in conversation phase, False if in planning
    accumulated_trip_info: Optional[RequiredTripFields]  # Accumulated trip details
    information_complete: bool  # Whether all required info is collected
    missing_fields: List[str]  # List of fields still needed
    next_question: Optional[str]  # Next question to ask user
    
    # State control
    current_step: str  # Current workflow step
    replan_counter: int  # Number of replans performed
    requires_clarification: bool  # Whether user input is needed
    
    # Layer 1: Intent & Constraints
    structured_request: Optional[TravelRequest]
    clarification: Optional[ClarificationRequest]
    constraints: Optional[ConstraintSet]
    budget_allocation: Optional[BudgetAllocation]
    
    # Layer 2: Data Retrieval (Agent Outputs)
    transport_options: Optional[List[TransportOption]]
    selected_transport_outbound: Optional[TransportOption]
    selected_transport_return: Optional[TransportOption]
    
    stay_options: Optional[List[StayOption]]
    selected_stay: Optional[StayOption]
    
    weather_data: Optional[WeatherData]
    attractions: Optional[AttractionList]
    
    # Layer 3: Synthesis
    itinerary: Optional[MultiDayItinerary]
    calendar_validation: Optional[CalendarValidation]
    
    # Layer 4: Optimization & Assessment
    optimization_results: Optional[OptimizationResults]
    risk_assessment: Optional[RiskSummary]
    confidence_score: Optional[float]
    confidence_explanation: Optional[str]
    
    # Output
    final_plan: Optional[FinalTravelPlan]
    
    # Audit & tracking
    audit_log: Annotated[List[AuditEntry], add]
    decision_log: Annotated[List[Decision], add]
    
    # Metadata
    workflow_start_time: Optional[datetime]
    total_token_usage: int
    
    # Error handling
    errors: Annotated[List[str], add]
    warnings: Annotated[List[str], add]


def create_initial_state(raw_query: str) -> TravelState:
    """
    Create initial state for a new travel planning request.
    
    Args:
        raw_query: The user's natural language query
        
    Returns:
        Initialized TravelState
    """
    return TravelState(
        # Input
        raw_query=raw_query,
        messages=[{"role": "user", "content": raw_query}],
        
        # NEW: Conversational layer initialization
        conversation_mode=True,
        accumulated_trip_info=RequiredTripFields(),
        information_complete=False,
        missing_fields=[],
        next_question=None,
        
        # Control
        current_step="conversation",
        replan_counter=0,
        requires_clarification=False,
        
        # Data (all None initially)
        structured_request=None,
        clarification=None,
        constraints=None,
        budget_allocation=None,
        
        transport_options=None,
        selected_transport_outbound=None,
        selected_transport_return=None,
        
        stay_options=None,
        selected_stay=None,
        
        weather_data=None,
        attractions=None,
        
        itinerary=None,
        calendar_validation=None,
        
        optimization_results=None,
        risk_assessment=None,
        confidence_score=None,
        confidence_explanation=None,
        
        final_plan=None,
        
        # Tracking
        audit_log=[],
        decision_log=[],
        
        workflow_start_time=datetime.now(),
        total_token_usage=0,
        
        errors=[],
        warnings=[]
    )


def log_agent_execution(
    state: TravelState,
    node_name: str,
    success: bool,
    duration_ms: float,
    token_usage: int = 0,
    errors: Optional[List[str]] = None
) -> None:
    """
    Log an agent execution to the audit log.
    
    Args:
        state: Current state
        node_name: Name of the agent/node
        success: Whether execution was successful
        duration_ms: Execution duration in milliseconds
        token_usage: Number of tokens used
        errors: List of errors if any
    """
    entry: AuditEntry = {
        "timestamp": datetime.now().isoformat(),
        "node": node_name,
        "action": "execute",
        "success": success,
        "duration_ms": duration_ms,
        "token_usage": token_usage if token_usage > 0 else None,
        "errors": errors
    }
    state["audit_log"].append(entry)
    
    if token_usage > 0:
        state["total_token_usage"] += token_usage


def add_decision(
    state: TravelState,
    component: str,
    decision: str,
    reasoning: str,
    alternatives_considered: int = 0
) -> None:
    """
    Add a decision to the decision log.
    
    Args:
        state: Current state
        component: Which component made the decision
        decision: What was decided
        reasoning: Why this decision was made
        alternatives_considered: How many alternatives were evaluated
    """
    from .output import Decision
    
    decision_entry = Decision(
        timestamp=datetime.now(),
        component=component,
        decision=decision,
        reasoning=reasoning,
        alternatives_considered=alternatives_considered
    )
    state["decision_log"].append(decision_entry.model_dump())
