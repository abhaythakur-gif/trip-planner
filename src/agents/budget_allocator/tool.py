"""
Tool functions for the Budget Allocator Agent.
Contains cost-of-living data and lookup utilities.
"""

# Cost of living multipliers for popular destinations (relative to global average = 1.0)
COST_MULTIPLIERS = {
    # High cost
    "london": 1.4, "paris": 1.3, "tokyo": 1.3, "new york": 1.4,
    "san francisco": 1.4, "zurich": 1.5, "oslo": 1.4, "singapore": 1.3,
    "sydney": 1.3, "hong kong": 1.3, "dubai": 1.2, "reykjavik": 1.4,
    # Medium cost
    "berlin": 1.0, "madrid": 1.0, "barcelona": 1.1, "rome": 1.1,
    "lisbon": 0.9, "prague": 0.8, "budapest": 0.7, "athens": 0.9,
    "dublin": 1.2, "amsterdam": 1.2, "vienna": 1.1, "milan": 1.2,
    # Low cost
    "bangkok": 0.5, "bali": 0.4, "hanoi": 0.4, "mumbai": 0.4,
    "mexico city": 0.6, "buenos aires": 0.6, "cairo": 0.5, "istanbul": 0.7,
    "marrakech": 0.6, "lima": 0.6, "bogota": 0.6, "manila": 0.4, "goa": 0.4,
}


def get_cost_multiplier(destination: str, multipliers: dict = None) -> float:
    """
    Return the cost-of-living multiplier for a destination.

    Args:
        destination: Lowercase destination string (may include country suffix).
        multipliers: Optional override dict; defaults to COST_MULTIPLIERS.

    Returns:
        Float multiplier (e.g. 1.3 = 30% more expensive than average).
    """
    if multipliers is None:
        multipliers = COST_MULTIPLIERS

    if destination in multipliers:
        return multipliers[destination]

    for city, multiplier in multipliers.items():
        if city in destination:
            return multiplier

    return 1.0  # Default for unknown destinations
