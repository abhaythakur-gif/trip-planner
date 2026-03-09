"""
Tool functions for the Constraint Modeler Agent.
Provides helper utilities for inferring soft-constraint values from user preferences.
"""


def infer_min_rating(comfort_level: int) -> float:
    """
    Map user comfort level (1-5) to minimum acceptable hotel star rating.

    Args:
        comfort_level: Integer 1 (budget) to 5 (luxury).

    Returns:
        Minimum hotel rating as a float.
    """
    rating_map = {
        1: 2.0,
        2: 2.5,
        3: 3.0,
        4: 3.5,
        5: 4.0,
    }
    return rating_map.get(comfort_level, 3.0)


def infer_max_activities(pace: str) -> int:
    """
    Map trip pace preference to maximum activities per day.

    Args:
        pace: One of "relaxed", "moderate", or "packed".

    Returns:
        Maximum number of activities per day as an integer.
    """
    pace_map = {
        "relaxed": 3,
        "moderate": 4,
        "packed": 6,
    }
    return pace_map.get(pace, 4)
