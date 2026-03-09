"""
Agent prompt templates - one module per agent that uses prompts.
"""

from .intent_extractor import (
    INTENT_EXTRACTION_PROMPT,
    get_intent_extraction_prompt,
)
from .constraint_modeler import (
    CONSTRAINT_MODELING_PROMPT,
    get_constraint_modeling_prompt,
)

__all__ = [
    "INTENT_EXTRACTION_PROMPT",
    "get_intent_extraction_prompt",
    "CONSTRAINT_MODELING_PROMPT",
    "get_constraint_modeling_prompt",
]
