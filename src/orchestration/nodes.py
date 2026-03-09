"""
Node functions for LangGraph workflow.
Each node function wraps an agent or performs a specific task.
"""

from typing import Dict, Any
from datetime import datetime
from ..schemas.state import TravelState
from ..agents.intent_extractor import IntentExtractorAgent
from ..agents.constraint_modeler import ConstraintModelerAgent
from ..agents.budget_allocator import BudgetAllocatorAgent
from ..agents.transport_search import TransportSearchAgent
from ..agents.stay_search import StaySearchAgent
from ..agents.weather import WeatherAgent
from ..agents.attractions import AttractionsAgent
from ..agents.itinerary_synthesis import ItinerarySynthesisAgent
from ..agents.optimization import OptimizationAgent
from ..agents.risk_assessment import RiskAssessmentAgent
# NEW: Conversational agents
from ..agents.conversation_manager import ConversationManagerAgent
from ..agents.information_checker import InformationCheckerAgent
from ..agents.question_generator import QuestionGeneratorAgent
from ..schemas.conversation import ConversationHistory, RequiredTripFields
from ..schemas.output import FinalTravelPlan, TripSummary, FallbackOption
from ..utils.logger import workflow_logger


# ========================================
# NEW: Conversational Layer Nodes
# ========================================

async def conversation_manager_node(state: TravelState) -> Dict[str, Any]:
    """
    Process user message and extract trip information.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates with extracted information
    """
    workflow_logger.info("Running conversation manager node")
    state["current_step"] = "conversation"
    
    # Get the last user message
    user_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            user_message = msg["content"]
            break
    
    if not user_message:
        workflow_logger.warning("No user message found")
        return {}
    
    # Build conversation history
    conv_history = ConversationHistory(
        messages=[msg for msg in state["messages"]]
    )
    
    # Get current accumulated fields
    current_fields = state.get("accumulated_trip_info") or RequiredTripFields()
    
    # Process the message
    agent = ConversationManagerAgent()
    updated_fields, acknowledgment = await agent.process(
        user_message,
        current_fields,
        conv_history
    )
    
    # Add acknowledgment to messages if there's new info
    updates = {
        "accumulated_trip_info": updated_fields,
    }
    
    if acknowledgment and acknowledgment != "Got it!":
        updates["messages"] = [{"role": "assistant", "content": acknowledgment}]
    
    return updates


async def information_checker_node(state: TravelState) -> Dict[str, Any]:
    """
    Check if all required information has been collected.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates with completeness status
    """
    workflow_logger.info("Running information checker node")
    
    accumulated_fields = state.get("accumulated_trip_info") or RequiredTripFields()
    
    # Build conversation context
    conv_context = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in state["messages"][-10:]  # Last 10 messages
    ])
    
    # Check completeness
    agent = InformationCheckerAgent()
    completeness = await agent.process(accumulated_fields, conv_context)
    
    workflow_logger.info(f"Information complete: {completeness.is_complete}")
    workflow_logger.info(f"Missing fields: {completeness.missing_fields}")
    
    return {
        "information_complete": completeness.is_complete,
        "missing_fields": completeness.missing_fields,
        "accumulated_trip_info": completeness.accumulated_info,
    }


async def question_generator_node(state: TravelState) -> Dict[str, Any]:
    """
    Generate follow-up question for missing information.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates with next question
    """
    workflow_logger.info("Running question generator node")
    
    missing_fields = state.get("missing_fields", [])
    accumulated_fields = state.get("accumulated_trip_info") or RequiredTripFields()
    
    # Build conversation history string
    conv_history = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in state["messages"][-5:]  # Last 5 messages
    ])
    
    # Generate question
    agent = QuestionGeneratorAgent()
    question = await agent.process(
        missing_fields,
        accumulated_fields,
        conv_history
    )
    
    workflow_logger.info(f"Generated question: {question}")
    
    return {
        "next_question": question,
        "messages": [{"role": "assistant", "content": question}]
    }


def should_continue_conversation(state: TravelState) -> str:
    """
    Conditional edge: decide if we should continue conversation or start planning.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name: "plan" or "question"
    """
    information_complete = state.get("information_complete", False)
    
    if information_complete:
        workflow_logger.info("✓ Information complete - transitioning to planning")
        return "plan"
    else:
        workflow_logger.info("⏩ Information incomplete - asking follow-up question")
        return "question"


async def transition_to_planning_node(state: TravelState) -> Dict[str, Any]:
    """
    Transition from conversation to planning phase.
    Converts accumulated fields to structured request.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates with final query for planning
    """
    workflow_logger.info("Transitioning to planning phase")
    
    accumulated_fields = state.get("accumulated_trip_info") or RequiredTripFields()
    
    # Convert accumulated fields to a natural language query
    final_query = accumulated_fields.to_query_string()
    
    workflow_logger.info(f"Final planning query: {final_query}")
    
    return {
        "conversation_mode": False,
        "current_step": "intent_extraction",
        "raw_query": final_query,
        "messages": [{"role": "system", "content": f"Starting trip planning with: {final_query}"}]
    }


# ========================================
# Existing Workflow Nodes
# ========================================

async def intent_extraction_node(state: TravelState) -> Dict[str, Any]:
    """
    Extract structured travel request from user query.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from intent extraction
    """
    workflow_logger.info("Running intent extraction node")
    
    agent = IntentExtractorAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "intent_extraction"
    
    return changes


async def constraint_modeling_node(state: TravelState) -> Dict[str, Any]:
    """
    Model constraints from the structured request.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from constraint modeling
    """
    workflow_logger.info("Running constraint modeling node")
    
    agent = ConstraintModelerAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "constraint_modeling"
    
    return changes


async def budget_allocation_node(state: TravelState) -> Dict[str, Any]:
    """
    Allocate budget across travel categories.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from budget allocation
    """
    workflow_logger.info("Running budget allocation node")
    
    agent = BudgetAllocatorAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "budget_allocation"
    
    return changes


async def transport_search_node(state: TravelState) -> Dict[str, Any]:
    """
    Search for transport options.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from transport search
    """
    workflow_logger.info("Running transport search node")
    
    agent = TransportSearchAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "transport_search"
    
    return changes


async def stay_search_node(state: TravelState) -> Dict[str, Any]:
    """
    Search for accommodation options.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from stay search
    """
    workflow_logger.info("Running stay search node")
    
    agent = StaySearchAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "stay_search"
    
    return changes


async def weather_fetch_node(state: TravelState) -> Dict[str, Any]:
    """
    Fetch weather data.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from weather fetch
    """
    workflow_logger.info("Running weather fetch node")
    
    agent = WeatherAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "weather_fetch"
    
    return changes


async def attractions_search_node(state: TravelState) -> Dict[str, Any]:
    """
    Search for attractions.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from attractions search
    """
    workflow_logger.info("Running attractions search node")
    
    agent = AttractionsAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "attractions_search"
    
    return changes


async def itinerary_synthesis_node(state: TravelState) -> Dict[str, Any]:
    """
    Synthesize complete itinerary.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from itinerary synthesis
    """
    workflow_logger.info("Running itinerary synthesis node")
    
    agent = ItinerarySynthesisAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "itinerary_synthesis"
    
    return changes


async def optimization_node(state: TravelState) -> Dict[str, Any]:
    """
    Optimize the travel plan.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from optimization
    """
    workflow_logger.info("Running optimization node")
    
    agent = OptimizationAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "optimization"
    
    return changes


async def risk_assessment_node(state: TravelState) -> Dict[str, Any]:
    """
    Assess risks and calculate confidence.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates from risk assessment
    """
    workflow_logger.info("Running risk assessment node")
    
    agent = RiskAssessmentAgent()
    changes = await agent.run(state)
    
    # Add current_step update
    changes["current_step"] = "risk_assessment"
    
    return changes


async def finalize_plan_node(state: TravelState) -> Dict[str, Any]:
    """
    Create final travel plan output.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates with final plan
    """
    workflow_logger.info("Running finalize plan node")
    
    changes = {"current_step": "finalize"}
    
    try:
        # Gather all components (some may be None)
        request = state.get("structured_request")
        budget = state.get("budget_allocation")
        transport_out = state.get("selected_transport_outbound")
        transport_ret = state.get("selected_transport_return")
        stay = state.get("selected_stay")
        itinerary = state.get("itinerary")
        risk = state.get("risk_assessment")
        confidence = state.get("confidence_score", 0.0)
        confidence_exp = state.get("confidence_explanation", "")
        decision_log = state.get("decision_log", [])
        total_tokens = state.get("total_token_usage", 0)
        replan_count = state.get("replan_counter", 0)
        workflow_start = state.get("workflow_start_time")
        
        # Check what's missing and log warnings
        missing_components = []
        if not request:
            missing_components.append("structured_request")
        if not budget:
            missing_components.append("budget_allocation")
        if not transport_out:
            missing_components.append("transport_outbound")
        if not transport_ret:
            missing_components.append("transport_return")
        if not stay:
            missing_components.append("accommodation")
        if not itinerary:
            missing_components.append("itinerary")
        if not risk:
            missing_components.append("risk_assessment")
        
        # If critical components are missing (request is essential), fail
        if not request:
            error_msg = "Cannot finalize plan: missing essential request data"
            workflow_logger.error(error_msg)
            changes["errors"] = [error_msg]
            return changes
        
        # Log warnings for missing non-critical components
        if missing_components:
            warning_msg = f"Finalizing incomplete plan - missing: {', '.join(missing_components)}"
            workflow_logger.warning(warning_msg)
            changes["warnings"] = [warning_msg]
            # Reduce confidence score for missing components
            confidence = max(0.0, confidence - (len(missing_components) * 0.1))
        
        # Calculate execution time
        if workflow_start:
            execution_time = (datetime.now() - workflow_start).total_seconds()
        else:
            execution_time = 0.0
        
        # Determine departure and return dates (with safe defaults)
        from datetime import timedelta
        
        if transport_out:
            departure_date = transport_out.departure
        elif request.start_date:
            # Convert date to datetime
            departure_date = datetime.combine(request.start_date, datetime.min.time())
        else:
            # Use today as default
            departure_date = datetime.now()
        
        if transport_ret:
            return_date = transport_ret.departure
        elif request.end_date:
            # Convert date to datetime
            return_date = datetime.combine(request.end_date, datetime.min.time())
        else:
            # Calculate based on duration or use default
            return_date = departure_date + timedelta(days=request.duration_days if request.duration_days else 7)
        
        # Create trip summary (use defaults for missing data)
        summary = TripSummary(
            destination=request.destination,
            origin=request.origin if request.origin else "Unknown",
            duration_days=request.duration_days if request.duration_days else 7,
            num_travelers=request.num_travelers if request.num_travelers else 1,
            departure_date=departure_date,
            return_date=return_date,
            total_budget=budget.total if budget else 0.0,
            total_cost=budget.spent_total if budget else 0.0,
            remaining_budget=budget.remaining if budget else 0.0,
            currency="USD",
        )
        
        # Create fallback options (empty if risk is missing)
        fallback_options = []
        if risk:
            for scenario in risk.scenarios:
                fallback = FallbackOption(
                    trigger=scenario.scenario_type,
                    alternative=scenario.fallback_recommendation,
                    additional_cost=scenario.estimated_additional_cost,
                )
                fallback_options.append(fallback)
        
        # Update confidence explanation if components are missing
        if missing_components:
            missing_note = f" Note: Plan is incomplete - missing {', '.join(missing_components)}."
            confidence_exp = (confidence_exp or "") + missing_note
        
        # Create final travel plan
        final_plan = FinalTravelPlan(
            summary=summary,
            budget_breakdown=budget,
            transport_outbound=transport_out,
            transport_return=transport_ret,
            accommodation=stay,
            daily_itinerary=itinerary,
            risk_summary=risk,
            fallback_options=fallback_options,
            confidence_score=confidence,
            confidence_explanation=confidence_exp,
            decision_log=decision_log,
            generated_at=datetime.now(),
            total_token_usage=total_tokens,
            replans_performed=replan_count,
            execution_time_seconds=execution_time,
        )
        
        # Store in state
        changes["final_plan"] = final_plan
        
        if missing_components:
            workflow_logger.warning(f"Travel plan finalized with missing components: {', '.join(missing_components)}")
        else:
            workflow_logger.info("Travel plan finalized successfully")
        
    except Exception as e:
        error_msg = f"Error finalizing plan: {type(e).__name__}: {str(e)}"
        workflow_logger.error(error_msg)
        changes["errors"] = [error_msg]
    
    return changes
