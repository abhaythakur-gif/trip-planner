"""
Main entry point for the travel planning system.
"""

import asyncio
from typing import Optional

from .schemas.output import FinalTravelPlan
from .orchestration import run_workflow
from .utils.logger import system_logger, workflow_logger
from .config import settings


async def plan_trip(query: str) -> Optional[FinalTravelPlan]:
    """
    Plan a trip from natural language query using LangGraph orchestration.
    
    This function now delegates to the LangGraph workflow which handles:
    - Intent extraction and constraint modeling
    - Budget allocation
    - Data retrieval (transport, stay, weather, attractions)
    - Itinerary synthesis
    - Optimization and risk assessment
    - Final plan generation
    
    Args:
        query: Natural language travel request
        
    Returns:
        FinalTravelPlan if successful, None if clarification needed
    """
    workflow_logger.info("Executing LangGraph workflow")
    return await run_workflow(query)


def main():
    """Main entry point."""
    print("🌍 AI Smart Travel Multi-Agent Planning System")
    print("🔗 Powered by LangGraph Multi-Agent Orchestration")
    print("=" * 60)
    
    # Example query
    query = """
    I want to plan a 5-day trip to Paris in May.
    My budget is $2500 and I'm traveling from New York.
    I love museums, good food, and prefer mid-range hotels.
    I like a moderate pace - not too rushed but want to see the highlights.
    """
    
    print(f"\n📝 Your request: {query.strip()}")
    print("\n" + "=" * 60)
    
    # Run the planning workflow with LangGraph orchestration
    result = asyncio.run(plan_trip(query))
    
    if result:
        print("\n🎉 Your travel plan is ready!")
        print(result.to_markdown())
    else:
        print("\n⏳ Continuing with remaining agent implementations...")
        print("✨ LangGraph workflow orchestration is active!")


if __name__ == "__main__":
    main()
