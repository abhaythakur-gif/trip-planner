"""
Tool functions for the Conversation Manager Agent.
Stateless helpers for parsing LLM extraction responses and field merging.
"""

import re
from typing import Any, Dict, Tuple

from ...schemas.conversation import RequiredTripFields


def parse_extraction_response(extraction: str) -> Dict[str, Any]:
    """Parse an LLM key: value extraction string into a typed dictionary."""
    lines = extraction.strip().split("\n")
    result: Dict[str, Any] = {}

    for line in lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")

        if not value or value in ("NONE", "None", "none", "[NONE]", "[None]", "[none]", "unknown", ""):
            continue

        if key == "duration_days":
            nums = re.findall(r"\d+", value)
            if nums:
                result[key] = int(nums[0])
        elif key == "budget":
            value_clean = value.lower().replace(",", "")
            if "k" in value_clean:
                nums = re.findall(r"[\d.]+", value_clean)
                if nums:
                    result[key] = float(nums[0]) * 1000
            else:
                nums = re.findall(r"[\d.]+", value_clean)
                if nums:
                    result[key] = float(nums[0])
        elif key == "travelers":
            nums = re.findall(r"\d+", value)
            if nums:
                result[key] = int(nums[0])
        else:
            result[key] = value

    return result


def merge_fields(current: RequiredTripFields, extracted: Dict[str, Any]) -> RequiredTripFields:
    """Merge extracted fields into current fields (never overwrite existing values except preferences)."""
    updates: Dict[str, Any] = {}

    for key, value in extracted.items():
        if not hasattr(current, key):
            continue
        current_value = getattr(current, key)
        if current_value is None or current_value == "" or (key == "travelers" and current_value == 1):
            updates[key] = value

    # Append new preferences instead of replacing
    if "preferences" in extracted and current.preferences:
        updates["preferences"] = f"{current.preferences}; {extracted['preferences']}"

    return current.model_copy(update=updates)


def generate_acknowledgment(extracted: Dict[str, Any]) -> str:
    """Build a brief user-facing acknowledgment of newly extracted information."""
    if not extracted:
        return "I understand."

    acks = []
    if "destination" in extracted:
        acks.append(f"Great choice with {extracted['destination']}!")
    if "start_date" in extracted:
        acks.append(f"Noted - {extracted['start_date']}")
    if "duration_days" in extracted:
        acks.append(f"{extracted['duration_days']} days sounds good")
    if "budget" in extracted:
        budget_val = extracted["budget"]
        if budget_val:
            acks.append(f"${budget_val:,.0f} budget noted")
    if "origin" in extracted:
        acks.append(f"traveling from {extracted['origin']}")
    if "travelers" in extracted:
        count = extracted["travelers"]
        if count > 1:
            acks.append(f"for {count} travelers")
    if "preferences" in extracted:
        acks.append("preferences noted")

    return ". ".join(acks[:2]) + "." if acks else "Got it!"
