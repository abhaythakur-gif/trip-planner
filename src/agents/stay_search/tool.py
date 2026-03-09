"""
Tool functions for the Stay Search Agent.
Handles hotel API searches, response parsing, fallback data, and scoring.
"""

from typing import List, Optional
from math import radians, sin, cos, sqrt, atan2

from ...schemas.agent_outputs import StayOption, GeoLocation
from ...utils.api_clients import serp_client

# Known city-centre coordinates for distance estimation
CITY_CENTERS = {
    "Paris": (48.8566, 2.3522),
    "London": (51.5074, -0.1278),
    "New York": (40.7128, -74.0060),
    "Tokyo": (35.6762, 139.6503),
    "Rome": (41.9028, 12.4964),
    "Barcelona": (41.3851, 2.1734),
}


def estimate_distance_to_center(lat: float, lon: float, city: str) -> float:
    """Estimate straight-line distance in km from a point to the city centre."""
    center = CITY_CENTERS.get(city, (lat, lon))

    lat1, lon1 = radians(center[0]), radians(center[1])
    lat2, lon2 = radians(lat), radians(lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(6371 * c, 2)


def determine_hotel_type(name: str) -> str:
    """Infer accommodation type from the property name."""
    name_lower = name.lower()
    if "hostel" in name_lower:
        return "hostel"
    if "resort" in name_lower or "spa" in name_lower:
        return "resort"
    if "apartment" in name_lower or "suite" in name_lower:
        return "apartment"
    return "hotel"


def get_amenities(type_: str, rating: float) -> List[str]:
    """Return a realistic amenities list based on accommodation type and rating."""
    base = ["WiFi", "Air Conditioning"]

    if type_ == "hotel":
        base.extend(["Room Service", "24-hour Reception", "Breakfast"])
        if rating >= 4.5:
            base.extend(["Spa", "Fitness Center", "Restaurant"])
    elif type_ == "apartment":
        base.extend(["Kitchen", "Washing Machine", "Living Room"])
    elif type_ == "hostel":
        base.extend(["Shared Kitchen", "Common Area", "Lockers"])
    elif type_ == "resort":
        base.extend(["Pool", "Spa", "Restaurant", "Bar", "Concierge"])

    return base


def parse_serp_hotel(prop: dict, request, nights: int) -> Optional[StayOption]:
    """
    Parse a SerpAPI Google Hotels property dict into a StayOption.

    SerpAPI structure:
        { "name", "rating", "reviews", "price": {"extracted_lowest": float},
          "gps_coordinates": {"latitude", "longitude"}, "address", "amenities", "type", ... }
    """
    name = prop.get("name", "Unknown Hotel")
    if not name:
        return None

    price_block = prop.get("price", {})
    price_per_night = float(
        price_block.get("extracted_lowest") or price_block.get("lowest") or 0
    )
    total_price = price_per_night * nights

    gps = prop.get("gps_coordinates", {})
    lat = float(gps.get("latitude", 0))
    lon = float(gps.get("longitude", 0))
    address = prop.get("address", "")
    city = request.destination.split(",")[0].strip()

    distance_to_center = estimate_distance_to_center(lat, lon, city)

    rating = float(prop.get("rating") or prop.get("class") or 4.0)
    if rating > 5:
        rating = 5.0

    num_reviews = int(prop.get("reviews") or 100)
    amenities = prop.get("amenities", []) or ["WiFi", "24-hour Reception"]

    hotel_type = determine_hotel_type(name)
    prop_type = prop.get("type", "")
    if prop_type:
        hotel_type = prop_type.lower()

    return StayOption(
        id=f"hotel_{hash(name) % 100000}",
        name=name,
        type=hotel_type,
        location=GeoLocation(
            latitude=lat,
            longitude=lon,
            address=address,
            city=city,
            country="",
        ),
        distance_to_center_km=distance_to_center,
        price_per_night=price_per_night,
        total_price=total_price,
        rating=rating,
        num_reviews=num_reviews,
        amenities=amenities,
        cancellation_policy="check property",
        free_cancellation_until=None,
    )


async def search_real_hotels(request, budget, constraints, logger=None) -> List[StayOption]:
    """Search for live hotel options via SerpAPI Google Hotels engine."""
    try:
        if not request.start_date:
            if logger:
                logger.warning("No travel dates available for hotel search")
            return []

        import datetime as dt_module

        nights = max(1, request.duration_days - 1)
        check_in = request.start_date.isoformat()
        check_out = (request.start_date + dt_module.timedelta(days=nights)).isoformat()
        city = request.destination.split(",")[0].strip()

        if logger:
            logger.info(f"Searching hotels in '{city}' from {check_in} to {check_out}")

        properties = await serp_client.search_hotels(
            destination=city,
            check_in_date=check_in,
            check_out_date=check_out,
            adults=request.num_travelers or 1,
            currency="USD",
            max_results=10,
        )

        if not properties:
            if logger:
                logger.warning(f"SerpAPI returned no hotels for '{city}'")
            return []

        options = []
        for i, prop in enumerate(properties):
            try:
                option = parse_serp_hotel(prop, request, nights)
                if option:
                    options.append(option)
            except Exception as e:
                if logger:
                    logger.warning(f"Error parsing SerpAPI hotel {i}: {e}")
                continue

        if logger:
            logger.info(f"Parsed {len(options)} hotel options from SerpAPI")
        return options

    except Exception as e:
        if logger:
            logger.error(f"Error in search_real_hotels (SerpAPI): {type(e).__name__}: {e}")
        return []


def generate_fallback_hotels(request, budget, constraints) -> List[StayOption]:
    """Generate fallback accommodation options when the live API is unavailable."""
    city = request.destination.split(",")[0].strip() if request.destination else "Unknown City"
    nights = max(1, request.duration_days - 1)
    base_price = (budget.stay / nights) if (budget and budget.stay and nights) else 100

    accommodations = [
        (f"{city} Grand Hotel", "hotel", 4.5, 500, 2.5),
        (f"{city} Cozy Apartment", "apartment", 4.3, 300, 1.8),
        (f"{city} Budget Hostel", "hostel", 4.0, 200, 3.5),
        (f"{city} Luxury Resort", "resort", 4.8, 800, 5.0),
    ]

    options = []
    for i, (name, type_, rating, num_reviews, dist_km) in enumerate(accommodations):
        price_per_night = base_price * (0.8 + i * 0.15)
        option = StayOption(
            id=f"stay_fallback_{i + 1}",
            name=name,
            type=type_,
            location=GeoLocation(
                latitude=0.0,
                longitude=0.0,
                address=f"{city} area",
                city=city,
                country="",
            ),
            distance_to_center_km=dist_km,
            price_per_night=price_per_night,
            total_price=price_per_night * nights,
            rating=rating,
            num_reviews=num_reviews,
            amenities=get_amenities(type_, rating),
            cancellation_policy="free cancellation" if i < 2 else "non-refundable",
            free_cancellation_until=request.start_date if i < 2 else None,
        )
        options.append(option)

    return options


def score_stay_options(options: List[StayOption], budget, constraints) -> List[StayOption]:
    """Score and rank stay options by price, location, quality, amenities and cancellation policy."""
    budget_per_night = budget.stay / max(1, budget.stay / 100)

    for option in options:
        if option.price_per_night <= budget_per_night:
            price_score = 100 - (option.price_per_night / budget_per_night * 30)
        else:
            price_score = max(0, 50 - (option.price_per_night / budget_per_night * 50))

        location_score = max(0, 100 - (option.distance_to_center_km * 10))
        quality_score = (option.rating / 5.0) * 100
        amenities_score = min(100, len(option.amenities) * 10)
        policy_bonus = 10 if option.cancellation_policy == "free cancellation" else 0

        option.score = (
            price_score * 0.35
            + location_score * 0.25
            + quality_score * 0.25
            + amenities_score * 0.10
            + policy_bonus * 0.05
        )

        if constraints and constraints.soft:
            preferred_types = constraints.soft.accommodation_types or []
            if preferred_types and option.type in preferred_types:
                option.score += 5

    return sorted(options, key=lambda x: x.score, reverse=True)
