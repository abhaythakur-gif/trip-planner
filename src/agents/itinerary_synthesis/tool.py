"""
Tool functions for the Itinerary Synthesis Agent.
Handles day-by-day schedule creation, activity selection, meal planning.
"""

from datetime import time, timedelta
from typing import List, Optional

from ...schemas.agent_outputs import (
    MultiDayItinerary,
    DailyItinerary,
    Activity,
    Meal,
    DailyForecast,
)

ACTIVITIES_PER_DAY = 3

DAY_THEMES = [
    "Arrival & iconic highlights",
    "Museums & cultural immersion",
    "Outdoor exploration & parks",
    "Hidden gems & local neighbourhoods",
    "Day trip or wider area excursion",
    "Art, shopping & leisure",
    "Final moments & farewell",
]

BREAKFAST_SPOTS = [
    "Hotel Buffet", "Local Café", "Bakery & Coffee Shop", "Street Market",
    "Hotel Breakfast", "Neighbourhood Crêperie", "Rooftop Café",
]
LUNCH_SPOTS = [
    "Local Bistro", "Street Food Market", "Riverside Restaurant", "Neighbourhood Brasserie",
    "Museum Café", "Covered Market", "Rooftop Restaurant",
]
DINNER_SPOTS = [
    "Fine Dining Restaurant", "Traditional Tavern", "Waterfront Brasserie",
    "Wine Bar & Tapas", "Michelin-Starred Bistro", "Rooftop Terrace Restaurant",
    "Hidden Gem Local Eatery",
]


def build_activity_pool(attractions_list, prefer_outdoor: bool) -> List:
    """Build a de-duplicated activity pool, preferred type first."""
    if prefer_outdoor:
        primary = list(attractions_list.outdoor_activities or [])
        secondary = list(attractions_list.indoor_activities or [])
    else:
        primary = list(attractions_list.indoor_activities or [])
        secondary = list(attractions_list.outdoor_activities or [])

    seen_ids: set = set()
    pool = []
    for a in primary + secondary + list(attractions_list.all_attractions or []):
        if a.id not in seen_ids:
            seen_ids.add(a.id)
            pool.append(a)
    return pool


def pick_day_attractions(pool: List, day_num: int) -> List:
    """Rotate through the pool to give each day unique attractions."""
    if not pool:
        return []
    pool_size = len(pool)
    start_idx = ((day_num - 1) * ACTIVITIES_PER_DAY) % pool_size
    end_idx = start_idx + ACTIVITIES_PER_DAY
    if end_idx <= pool_size:
        return pool[start_idx:end_idx]
    return (pool[start_idx:] + pool[: end_idx - pool_size])[:ACTIVITIES_PER_DAY]


def build_activities(selected_attractions) -> List[Activity]:
    """Convert attraction list into timed Activity objects."""
    activities = []
    current_time = time(9, 0)

    for idx, attraction in enumerate(selected_attractions):
        duration_hours = attraction.estimated_duration_hours
        end_hour = current_time.hour + int(duration_hours)
        end_minute = current_time.minute + int((duration_hours % 1) * 60)

        if end_minute >= 60:
            end_hour += 1
            end_minute -= 60

        end_time = time(min(23, end_hour), min(59, end_minute))
        travel_time = 20 if idx > 0 else 0

        activities.append(
            Activity(
                time_start=current_time,
                time_end=end_time,
                attraction=attraction,
                travel_time_minutes=travel_time,
                notes=["Book in advance" if attraction.requires_booking else ""],
            )
        )

        next_hour = end_hour + 1
        if next_hour < 24:
            current_time = time(next_hour, 0)
        else:
            break

    return activities


def build_meals(day_num: int) -> List[Meal]:
    """Build a varied set of meals for the day."""
    idx = (day_num - 1) % 7
    return [
        Meal(type="breakfast", location=BREAKFAST_SPOTS[idx], estimated_cost=15.0, time=time(8, 0)),
        Meal(type="lunch", location=LUNCH_SPOTS[idx], estimated_cost=25.0, time=time(13, 0)),
        Meal(type="dinner", location=DINNER_SPOTS[idx], estimated_cost=40.0, time=time(19, 30)),
    ]


def create_default_weather(day_date) -> DailyForecast:
    """Return a neutral default weather forecast."""
    return DailyForecast(
        date=day_date,
        temp_min=15.0,
        temp_max=25.0,
        temp_avg=20.0,
        condition="partly cloudy",
        precipitation_probability=0.3,
        precipitation_mm=0.0,
        wind_speed_kmh=10.0,
        humidity_percent=60.0,
        is_good_for_outdoor=True,
    )


def resolve_day_weather(weather, day_num: int, day_date) -> DailyForecast:
    """
    Return a DailyForecast for the given trip day, using forecast index.
    Falls back to a default if no forecast data is available.
    """
    if not (weather and weather.forecasts):
        return create_default_weather(day_date)

    forecast_index = day_num - 1
    if forecast_index < len(weather.forecasts):
        orig = weather.forecasts[forecast_index]
    elif weather.forecasts:
        orig = weather.forecasts[0]
    else:
        return create_default_weather(day_date)

    # Re-stamp the forecast with the actual trip date
    return DailyForecast(
        date=day_date,
        temp_min=orig.temp_min,
        temp_max=orig.temp_max,
        temp_avg=orig.temp_avg,
        condition=orig.condition,
        precipitation_probability=orig.precipitation_probability,
        precipitation_mm=orig.precipitation_mm,
        wind_speed_kmh=orig.wind_speed_kmh,
        humidity_percent=orig.humidity_percent,
        sunrise=getattr(orig, "sunrise", None),
        sunset=getattr(orig, "sunset", None),
        is_good_for_outdoor=orig.is_good_for_outdoor,
    )


def create_daily_itinerary(
    day_num: int,
    day_date,
    day_weather: DailyForecast,
    attractions_list,
    budget,
) -> DailyItinerary:
    """Create a full itinerary for a single day."""
    pool = build_activity_pool(attractions_list, prefer_outdoor=day_weather.is_good_for_outdoor) if attractions_list else []
    selected = pick_day_attractions(pool, day_num)
    activities = build_activities(selected)
    meals = build_meals(day_num)

    activity_cost = sum(a.attraction.cost for a in activities)
    meal_cost = sum(m.estimated_cost for m in meals)
    day_theme = DAY_THEMES[(day_num - 1) % len(DAY_THEMES)]

    return DailyItinerary(
        day_number=day_num,
        date=day_date,
        weather=day_weather,
        activities=activities,
        meals=meals,
        total_cost=activity_cost + meal_cost,
        total_walking_distance_km=len(activities) * 2.5,
        estimated_transit_time_hours=sum(a.travel_time_minutes for a in activities) / 60.0,
        notes=[f"Day {day_num} theme: {day_theme}", f"Weather: {day_weather.condition}"],
    )


def build_full_itinerary(
    request,
    weather,
    attractions_list,
    budget,
    logger=None,
) -> MultiDayItinerary:
    """Build a complete multi-day itinerary."""
    from datetime import date as date_cls

    current_date = request.start_date if request.start_date else date_cls.today()
    duration_days = request.duration_days or 7

    daily_itineraries = []
    total_cost = 0.0

    for day_num in range(1, duration_days + 1):
        day_date = current_date + timedelta(days=day_num - 1)
        day_weather = resolve_day_weather(weather, day_num, day_date)
        daily = create_daily_itinerary(day_num, day_date, day_weather, attractions_list, budget)
        daily_itineraries.append(daily)
        total_cost += daily.total_cost

    if logger:
        logger.debug(f"Built {len(daily_itineraries)}-day itinerary, total cost ${total_cost:.2f}")

    return MultiDayItinerary(days=daily_itineraries, total_cost=total_cost)
