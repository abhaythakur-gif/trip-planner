"""
Tool functions for the Information Checker Agent.
Pure-Python helpers that do not depend on the agent class.
"""

import re
from typing import Optional

from ...schemas.conversation import RequiredTripFields


def parse_llm_extraction(extraction: str, current_fields: RequiredTripFields) -> RequiredTripFields:
    """
    Parse an LLM key: value extraction response and update the supplied fields.

    Only fields that are currently unset are updated; existing values are kept.
    """
    lines = extraction.strip().split("\n")
    updates = {}

    for line in lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if not value or value in ("NONE", "None", "[NONE]", "[None]", "none", "[none]"):
            continue

        if key == "destination" and not current_fields.destination:
            updates["destination"] = value
        elif key == "origin" and not current_fields.origin:
            updates["origin"] = value
        elif key == "start_date" and not current_fields.start_date:
            updates["start_date"] = value
        elif key == "end_date" and not current_fields.end_date:
            updates["end_date"] = value
        elif key == "duration_days" and not current_fields.duration_days:
            try:
                updates["duration_days"] = int(value)
            except ValueError:
                pass
        elif key == "budget" and not current_fields.budget:
            nums = re.findall(r"\d+", value.replace(",", ""))
            if nums:
                updates["budget"] = float(nums[0])
        elif key == "travelers" and current_fields.travelers == 1:
            try:
                updates["travelers"] = int(value)
            except ValueError:
                pass
        elif key == "preferences":
            if current_fields.preferences:
                updates["preferences"] = f"{current_fields.preferences}; {value}"
            else:
                updates["preferences"] = value

    return current_fields.model_copy(update=updates)
