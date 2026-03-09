"""
Tool functions for the Transport Search Agent.
Handles IATA lookup, SerpAPI flight search, fallback options, scoring and return-flight synthesis.
"""

import re
from typing import List
from datetime import datetime, timedelta

from ...schemas.agent_outputs import TransportOption
from ...utils.api_clients import serp_client

# ---------------------------------------------------------------------------
# DATA: City → IATA airport code mapping
# ---------------------------------------------------------------------------
AIRPORT_CODES = {
    # India
    "mumbai": "BOM", "delhi": "DEL", "new delhi": "DEL",
    "bangalore": "BLR", "bengaluru": "BLR",
    "hyderabad": "HYD", "chennai": "MAA", "kolkata": "CCU",
    "goa": "GOI", "jaipur": "JAI", "ahmedabad": "AMD",
    "kochi": "COK", "pune": "PNQ", "lucknow": "LKO",
    "amritsar": "ATQ", "varanasi": "VNS", "agra": "AGR",
    "bhopal": "BHO", "nagpur": "NAG", "srinagar": "SXR",
    "leh": "IXL", "port blair": "IXZ",
    # Europe
    "paris": "CDG", "london": "LHR", "rome": "FCO",
    "barcelona": "BCN", "amsterdam": "AMS", "berlin": "BER",
    "madrid": "MAD", "vienna": "VIE", "prague": "PRG",
    "lisbon": "LIS", "athens": "ATH", "dublin": "DUB",
    "zurich": "ZRH", "brussels": "BRU", "istanbul": "IST",
    "milan": "MXP", "munich": "MUC", "frankfurt": "FRA",
    # Americas
    "new york": "JFK", "los angeles": "LAX", "chicago": "ORD",
    "miami": "MIA", "san francisco": "SFO", "seattle": "SEA",
    "toronto": "YYZ", "vancouver": "YVR", "boston": "BOS",
    "washington": "IAD", "las vegas": "LAS",
    # Asia Pacific
    "tokyo": "NRT", "singapore": "SIN", "hong kong": "HKG",
    "bangkok": "BKK", "dubai": "DXB", "shanghai": "PVG",
    "beijing": "PEK", "seoul": "ICN", "kuala lumpur": "KUL",
    "sydney": "SYD", "melbourne": "MEL", "bali": "DPS",
    "phuket": "HKT", "taipei": "TPE",
}


def get_airport_code(city_name: str) -> str:
    """Return the IATA airport code for a given city name."""
    city_clean = re.sub(r"[,\.].*", "", city_name.lower().strip()).strip()
    return AIRPORT_CODES.get(city_clean, city_name[:3].upper())


async def search_real_flights(
    origin: str, destination: str, request, budget, logger=None
) -> List[TransportOption]:
    """Search for real flights via SerpAPI Google Flights engine."""
    try:
        departure_date = request.start_date.strftime("%Y-%m-%d")
        return_date = ""
        if request.travel_dates and request.travel_dates.end:
            return_date = request.travel_dates.end.strftime("%Y-%m-%d")

        data = await serp_client.search_flights(
            origin_iata=origin,
            destination_iata=destination,
            outbound_date=departure_date,
            return_date=return_date,
            adults=request.num_travelers or 1,
            currency="USD",
        )

        if not data:
            return []

        all_groups = data.get("best_flights", []) + data.get("other_flights", [])
        if not all_groups:
            return []

        options = []
        for i, group in enumerate(all_groups[:10]):
            try:
                flights = group.get("flights", [])
                if not flights:
                    continue

                first_leg = flights[0]
                last_leg = flights[-1]

                dep_info = first_leg.get("departure_airport", {})
                arr_info = last_leg.get("arrival_airport", {})

                dep_dt = datetime.strptime(dep_info.get("time", ""), "%Y-%m-%d %H:%M")
                arr_dt = datetime.strptime(arr_info.get("time", ""), "%Y-%m-%d %H:%M")

                duration = int(group.get("total_duration", 0))
                if duration == 0:
                    duration = int((arr_dt - dep_dt).total_seconds() / 60)

                price = float(group.get("price", 0))
                airline = first_leg.get("airline", "Unknown Airline")
                flight_num = first_leg.get("flight_number", f"FLT{i + 1}")
                num_stops = len(flights) - 1
                travel_class = first_leg.get("travel_class", "Economy")

                option = TransportOption(
                    id=f"flight_{i + 1}",
                    type="flight",
                    origin=dep_info.get("id", origin),
                    destination=arr_info.get("id", destination),
                    departure=dep_dt,
                    arrival=arr_dt,
                    duration_minutes=duration,
                    price=price,
                    carrier=airline,
                    flight_number=flight_num,
                    stops=num_stops,
                    cabin_class=travel_class.lower(),
                    cancellation_policy="varies",
                    baggage_included=True,
                )
                options.append(option)

            except Exception as e:
                if logger:
                    logger.warning(f"Error parsing SerpAPI flight group {i}: {e}")
                continue

        return options

    except Exception as e:
        if logger:
            logger.error(f"Error in SerpAPI flight search: {type(e).__name__}: {e}")
        return []


def generate_fallback_transport(request, budget) -> List[TransportOption]:
    """Generate fallback flight options when the live API is unavailable."""
    from datetime import date as date_type, datetime as dt_type

    start = request.start_date
    if start is None:
        start = dt_type.now()
    if type(start) is date_type:
        start = dt_type.combine(start, dt_type.min.time())

    carriers = [
        ("IndiGo", "6E100", 0.9),
        ("Air India", "AI200", 0.85),
        ("SpiceJet", "SG300", 0.75),
    ]

    options = []
    for i, (carrier, flight_num, _quality_factor) in enumerate(carriers):
        base_price = budget.transport * 0.4 * (1 + i * 0.15)
        option = TransportOption(
            id=f"transport_{i + 1}",
            type="flight",
            origin=request.origin,
            destination=request.destination,
            departure=start,
            arrival=start + timedelta(hours=8),
            duration_minutes=480,
            price=base_price,
            carrier=carrier,
            flight_number=flight_num,
            stops=0 if i == 0 else i - 1,
            cabin_class="economy",
            cancellation_policy="refundable" if i == 0 else "non-refundable",
            baggage_included=True,
        )
        options.append(option)

    return options


def score_transport_options(options: List[TransportOption], budget: float) -> List[TransportOption]:
    """Score and rank transport options (lower price + shorter time + quality = higher score)."""
    for option in options:
        price_score = max(0, 100 - (option.price / budget * 100))
        time_score = max(0, 100 - (option.duration_minutes / 600 * 50))

        quality_score = 100 if option.stops == 0 else 70
        if option.cancellation_policy == "refundable":
            quality_score += 10

        option.score = price_score * 0.5 + time_score * 0.3 + quality_score * 0.2

    return sorted(options, key=lambda x: x.score, reverse=True)


def build_return_flight(outbound: TransportOption, request) -> TransportOption:
    """Synthesize a return flight based on the selected outbound flight."""
    from datetime import date as date_type, datetime as dt_type

    end_date = request.end_date
    if end_date is None:
        start = request.start_date
        duration = request.duration_days or 7
        if isinstance(start, date_type):
            end_date = dt_type.combine(start, dt_type.min.time()) + timedelta(days=duration - 1)
        else:
            end_date = start + timedelta(days=duration - 1)

    if type(end_date) is date_type:
        end_date = dt_type.combine(end_date, dt_type.min.time())

    return TransportOption(
        id=f"{outbound.id}_return",
        type=outbound.type,
        origin=outbound.destination,
        destination=outbound.origin,
        departure=end_date,
        arrival=end_date + timedelta(hours=int(outbound.duration_minutes / 60)),
        duration_minutes=outbound.duration_minutes,
        price=outbound.price * 1.05,
        carrier=outbound.carrier,
        flight_number=f"{outbound.flight_number}R" if outbound.flight_number else None,
        stops=outbound.stops,
        cabin_class=outbound.cabin_class,
        cancellation_policy=outbound.cancellation_policy,
        baggage_included=outbound.baggage_included,
        score=outbound.score,
    )
