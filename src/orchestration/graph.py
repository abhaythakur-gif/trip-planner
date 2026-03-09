"""
LangGraph workflow definition for travel planning.
Defines the StateGraph with nodes, edges, and conditional routing.
"""

from typing import Literal, Optional
from langgraph.graph import StateGraph, END
from ..schemas.state import TravelState, create_initial_state
from ..schemas.output import FinalTravelPlan
from ..utils.logger import workflow_logger
from .nodes import (
    # NEW: Conversational layer nodes
    conversation_manager_node,
    information_checker_node,
    question_generator_node,
    should_continue_conversation,
    transition_to_planning_node,
    # Existing workflow nodes
    intent_extraction_node,
    constraint_modeling_node,
    budget_allocation_node,
    transport_search_node,
    stay_search_node,
    weather_fetch_node,
    attractions_search_node,
    itinerary_synthesis_node,
    optimization_node,
    risk_assessment_node,
    finalize_plan_node,
)


# NEW: Conversational layer node names
CONVERSATION_MANAGER = "conversation_manager"
INFORMATION_CHECKER = "information_checker"
QUESTION_GENERATOR = "question_generator"
TRANSITION_TO_PLANNING = "transition_to_planning"

# Node name constants
INTENT_EXTRACTION = "intent_extraction"
CONSTRAINT_MODELING = "constraint_modeling"
BUDGET_ALLOCATION = "budget_allocation"
TRANSPORT_SEARCH = "transport_search"
STAY_SEARCH = "stay_search"
WEATHER_FETCH = "weather_fetch"
ATTRACTIONS_SEARCH = "attractions_search"
ITINERARY_SYNTHESIS = "itinerary_synthesis"
OPTIMIZATION = "optimization"
RISK_ASSESSMENT = "risk_assessment"
FINALIZE = "finalize"


def should_continue_after_intent(
    state: TravelState,
) -> Literal["constraint_modeling", "__end__"]:
    """
    Conditional edge: decide whether to continue or end after intent extraction.
    
    If clarification is required, we end the workflow so the user can provide more info.
    Otherwise, continue to constraint modeling.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name or END
    """
    if state.get("requires_clarification", False):
        workflow_logger.info("Clarification required - ending workflow for user input")
        return END
    
    workflow_logger.info("Intent extraction complete - proceeding to constraint modeling")
    return CONSTRAINT_MODELING


def should_replan(state: TravelState) -> Literal["intent_extraction", "finalize"]:
    """
    Conditional edge: decide whether to replan or finalize.
    
    Check if replanning is needed based on optimization results or risk assessment.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name
    """
    # Check replan counter to avoid infinite loops
    replan_counter = state.get("replan_counter", 0)
    max_replans = 2  # Maximum number of replanning attempts
    
    if replan_counter >= max_replans:
        workflow_logger.info(f"Max replans ({max_replans}) reached - finalizing plan")
        return FINALIZE
    
    # Check if confidence is too low and replanning would help
    confidence = state.get("confidence_score", 1.0)
    if confidence is not None and confidence < 0.6:
        workflow_logger.info(f"Low confidence ({confidence:.2f}) - considering replan")
        
        # Check if we have meaningful constraints to try adjusting
        # For now, just finalize - replanning logic can be enhanced later
        workflow_logger.info("Replanning logic not yet implemented - finalizing")
        return FINALIZE
    
    workflow_logger.info("No replan needed - finalizing plan")
    return FINALIZE


def create_travel_planning_graph() -> StateGraph:
    """
    Create and configure the travel planning StateGraph.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    workflow_logger.info("Creating travel planning StateGraph")
    
    # Initialize the graph with TravelState
    graph = StateGraph(TravelState)
    
    # ===== Add all nodes =====
    workflow_logger.debug("Adding nodes to graph")
    
    # NEW: Conversational Layer (runs first)
    graph.add_node(CONVERSATION_MANAGER, conversation_manager_node)
    graph.add_node(INFORMATION_CHECKER, information_checker_node)
    graph.add_node(QUESTION_GENERATOR, question_generator_node)
    graph.add_node(TRANSITION_TO_PLANNING, transition_to_planning_node)
    
    # Layer 1: Intent & Constraints
    graph.add_node(INTENT_EXTRACTION, intent_extraction_node)
    graph.add_node(CONSTRAINT_MODELING, constraint_modeling_node)
    graph.add_node(BUDGET_ALLOCATION, budget_allocation_node)
    
    # Layer 2: Data Retrieval (parallel candidates)
    graph.add_node(TRANSPORT_SEARCH, transport_search_node)
    graph.add_node(STAY_SEARCH, stay_search_node)
    graph.add_node(WEATHER_FETCH, weather_fetch_node)
    graph.add_node(ATTRACTIONS_SEARCH, attractions_search_node)
    
    # Layer 3: Synthesis
    graph.add_node(ITINERARY_SYNTHESIS, itinerary_synthesis_node)
    
    # Layer 4: Optimization & Assessment
    graph.add_node(OPTIMIZATION, optimization_node)
    graph.add_node(RISK_ASSESSMENT, risk_assessment_node)
    
    # Output
    graph.add_node(FINALIZE, finalize_plan_node)
    
    # ===== Define workflow edges =====
    workflow_logger.debug("Adding edges to graph")
    
    # NEW: Set entry point to conversational layer
    graph.set_entry_point(CONVERSATION_MANAGER)
    
    # NEW: Conversational flow
    graph.add_edge(CONVERSATION_MANAGER, INFORMATION_CHECKER)
    
    # NEW: Conditional: complete info -> planning, incomplete -> ask question
    graph.add_conditional_edges(
        INFORMATION_CHECKER,
        should_continue_conversation,
        {
            "plan": TRANSITION_TO_PLANNING,
            "question": QUESTION_GENERATOR,
        }
    )
    
    # NEW: After question, wait for user response (END for now, UI will handle)
    graph.add_edge(QUESTION_GENERATOR, END)
    
    # NEW: Transition from conversation to planning
    graph.add_edge(TRANSITION_TO_PLANNING, INTENT_EXTRACTION)
    
    # Layer 1: Intent -> Constraint -> Budget
    # Conditional: check if clarification needed after intent extraction
    graph.add_conditional_edges(
        INTENT_EXTRACTION,
        should_continue_after_intent,
        {
            CONSTRAINT_MODELING: CONSTRAINT_MODELING,
            END: END,
        }
    )
    
    # Continue through Layer 1
    graph.add_edge(CONSTRAINT_MODELING, BUDGET_ALLOCATION)
    
    # After budget allocation, trigger parallel data retrieval
    # For now, we'll do sequential flow (can be parallelized later with proper LangGraph patterns)
    graph.add_edge(BUDGET_ALLOCATION, TRANSPORT_SEARCH)
    graph.add_edge(TRANSPORT_SEARCH, STAY_SEARCH)
    graph.add_edge(STAY_SEARCH, WEATHER_FETCH)
    graph.add_edge(WEATHER_FETCH, ATTRACTIONS_SEARCH)
    
    # Layer 3: Synthesis
    graph.add_edge(ATTRACTIONS_SEARCH, ITINERARY_SYNTHESIS)
    
    # Layer 4: Optimization & Assessment
    graph.add_edge(ITINERARY_SYNTHESIS, OPTIMIZATION)
    graph.add_edge(OPTIMIZATION, RISK_ASSESSMENT)
    
    # Conditional: check if replanning needed or finalize
    graph.add_conditional_edges(
        RISK_ASSESSMENT,
        should_replan,
        {
            INTENT_EXTRACTION: INTENT_EXTRACTION,  # Replan
            FINALIZE: FINALIZE,  # Finalize
        }
    )
    
    # End after finalization
    graph.add_edge(FINALIZE, END)
    
    # ===== Compile the graph =====
    workflow_logger.info("Compiling StateGraph")
    compiled_graph = graph.compile()
    
    workflow_logger.info("StateGraph created successfully")
    return compiled_graph


async def run_workflow(query: str) -> Optional[FinalTravelPlan]:
    """
    Run the complete travel planning workflow.
    
    Args:
        query: Natural language travel request from user
        
    Returns:
        FinalTravelPlan if successful, None if clarification needed
    """
    workflow_logger.info(f"Starting workflow for query: {query[:100]}...")
    
    # Create initial state
    initial_state = create_initial_state(query)
    
    # Get the compiled graph
    graph = create_travel_planning_graph()
    
    # Execute the workflow
    try:
        workflow_logger.info("Executing workflow graph")
        final_state = await graph.ainvoke(initial_state)
        
        # Check if clarification was requested
        if final_state.get("requires_clarification"):
            clarification = final_state.get("clarification")
            if clarification:
                workflow_logger.info("Workflow ended - clarification required")
                print("\n🤔 I need some more information:")
                for question in clarification.get("questions", []):
                    print(f"  - {question}")
                return None
        
        # Check for errors
        errors = final_state.get("errors", [])
        if errors:
            workflow_logger.warning(f"Workflow completed with {len(errors)} errors")
            for error in errors:
                print(f"⚠️  {error}")
        
        # Display progress summary
        request = final_state.get("structured_request")
        budget = final_state.get("budget_allocation")
        
        if request and budget:
            print("\n✅ Planning your trip!")
            print(f"📍 Destination: {request.destination}")
            print(f"📅 Duration: {request.duration_days} days")
            print(f"💰 Budget: ${budget.total:.2f}")
            print(f"   - Transport: ${budget.transport:.2f}")
            print(f"   - Stay: ${budget.stay:.2f}")
            print(f"   - Food: ${budget.food:.2f}")
            print(f"   - Activities: ${budget.activities:.2f}")
            print(f"   - Buffer: ${budget.buffer:.2f}")
        
        # Display warnings
        warnings = final_state.get("warnings", [])
        if warnings:
            print(f"\n⚠️  {len(warnings)} components not yet implemented:")
            for warning in warnings:
                print(f"   - {warning}")
        
        # Log audit trail
        audit_log = final_state.get("audit_log", [])
        workflow_logger.info(f"Workflow completed with {len(audit_log)} agent executions")
        
        total_tokens = final_state.get("total_token_usage", 0)
        workflow_logger.info(f"Total token usage: {total_tokens}")
        
        # Return final plan (if available)
        final_plan = final_state.get("final_plan")
        
        if final_plan:
            workflow_logger.info("Final travel plan generated")
        else:
            workflow_logger.info("Workflow complete (partial implementation)")
            print("\n✨ LangGraph workflow executed successfully!")
            print("📊 Full travel plan generation coming soon with remaining agent implementations")
        
        return final_plan
        
    except Exception as e:
        workflow_logger.error(f"Workflow execution failed: {type(e).__name__}: {str(e)}")
        print(f"\n❌ Workflow failed: {str(e)}")
        raise
