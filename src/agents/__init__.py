"""
Agents package - re-exports all agent classes for backward-compatible imports.

New modular structure:
  src/agents/<agent_name>/
      __init__.py  - re-exports the agent class
      agent.py     - agent class implementation
      tool.py      - pure tool/helper functions

Usage:
    from src.agents import AttractionsAgent
    from src.agents.attractions import AttractionsAgent  # also valid
"""

from .attractions import AttractionsAgent
from .budget_allocator import BudgetAllocatorAgent
from .constraint_modeler import ConstraintModelerAgent
from .intent_extractor import IntentExtractorAgent
from .information_checker import InformationCheckerAgent
from .itinerary_synthesis import ItinerarySynthesisAgent
from .optimization import OptimizationAgent
from .question_generator import QuestionGeneratorAgent
from .conversation_manager import ConversationManagerAgent
from .risk_assessment import RiskAssessmentAgent
from .stay_search import StaySearchAgent
from .transport_search import TransportSearchAgent
from .weather import WeatherAgent

__all__ = [
    "AttractionsAgent",
    "BudgetAllocatorAgent",
    "ConstraintModelerAgent",
    "ConversationManagerAgent",
    "InformationCheckerAgent",
    "IntentExtractorAgent",
    "ItinerarySynthesisAgent",
    "OptimizationAgent",
    "QuestionGeneratorAgent",
    "RiskAssessmentAgent",
    "StaySearchAgent",
    "TransportSearchAgent",
    "WeatherAgent",
]
