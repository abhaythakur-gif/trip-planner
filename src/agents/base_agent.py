"""
Base agent class for all travel planning agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import time
from datetime import datetime

from ..schemas.state import TravelState, log_agent_execution
from ..utils.logger import get_logger


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    All agents must:
    1. Implement the execute() method
    2. Read from state
    3. Write only to their designated state fields
    4. Log their execution
    5. Handle errors gracefully
    """
    
    def __init__(self, name: str):
        """
        Initialize agent.
        
        Args:
            name: Agent name for logging
        """
        self.name = name
        self.logger = get_logger(f"trip_planner.agents.{name}")
    
    @abstractmethod
    async def execute(self, state: TravelState) -> TravelState:
        """
        Execute the agent's task.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        pass
    
    async def run(self, state: TravelState) -> Dict[str, Any]:
        """
        Run the agent with error handling and logging.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary containing only the updated state fields (for LangGraph merging)
        """
        self.logger.info(f"Starting {self.name} agent")
        start_time = time.time()
        
        try:
            # Create a shallow copy to track what changes
            original_state = dict(state)
            
            # Execute agent logic
            updated_state = await self.execute(state)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log success
            log_agent_execution(
                updated_state,
                self.name,
                success=True,
                duration_ms=duration_ms
            )
            
            self.logger.info(
                f"{self.name} completed successfully",
                extra={"duration_ms": duration_ms}
            )
            
            # Extract only the changed fields for LangGraph state merging
            # This is critical for TypedDict-based state propagation
            changes = self._extract_changes(original_state, updated_state)
            
            return changes
            
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Use original_state if it exists (from try block), otherwise use state
            current_state = state if 'original_state' not in locals() else state
            
            # Log failure
            error_msg = f"{type(e).__name__}: {str(e)}"
            log_agent_execution(
                current_state,
                self.name,
                success=False,
                duration_ms=duration_ms,
                errors=[error_msg]
            )
            
            # Log with full error details
            self.logger.error(
                f"{self.name} failed: {error_msg}",
                extra={"duration_ms": duration_ms}
            )
            
            # Also log the full traceback for debugging
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return error update
            return {
                "errors": current_state.get("errors", []) + [f"{self.name}: {error_msg}"]
            }
    
    def _extract_changes(self, old_state: TravelState, new_state: TravelState) -> Dict[str, Any]:
        """
        Extract only the fields that changed between old and new state.
        
        Args:
            old_state: Original state
            new_state: Updated state
            
        Returns:
            Dictionary with only changed fields
        """
        changes = {}
        
        # Check each field in the new state
        for key, new_value in new_state.items():
            old_value = old_state.get(key)
            
            # For lists with Annotated[List, add], always include them
            # as LangGraph will append them
            if key in ["messages", "audit_log", "decision_log", "errors", "warnings"]:
                # Only include if there's new content
                if new_value and len(new_value) > len(old_value or []):
                    # Return only the new items
                    old_len = len(old_value or [])
                    changes[key] = new_value[old_len:]
            # For other fields, include if changed
            elif new_value != old_value:
                changes[key] = new_value
        
        return changes
    
    def log_decision(
        self,
        state: TravelState,
        decision: str,
        reasoning: str,
        alternatives: int = 0
    ) -> None:
        """
        Log a decision made by this agent.
        
        Args:
            state: Current state
            decision: What was decided
            reasoning: Why it was decided
            alternatives: Number of alternatives considered
        """
        from ..schemas.state import add_decision
        
        add_decision(
            state,
            component=self.name,
            decision=decision,
            reasoning=reasoning,
            alternatives_considered=alternatives
        )
