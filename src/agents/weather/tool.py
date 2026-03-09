"""
Tool functions for the Weather Agent.
Uses Open-Meteo API (free, no API key required).
"""

from typing import List, Optional
from datetime import date, time, timedelta, datetime

from ...schemas.agent_outputs import WeatherData, DailyForecast, WeatherRisk
from ...utils.api_clients import weather_client


def weather_code_to_condition(code: int) -> str:
    """
    Convert Open-Meteo weather code to human-readable condition.
    See: https://open-meteo.com/en/docs
    """
    if code == 0:
        return "clear"
    elif code in [1, 2]:
        return "partly cloudy"
    elif code == 3:
        return "overcast"
    elif code in [45, 48]:
        return "foggy"
    elif code in [51, 53, 55, 56, 57]:
        return "drizzle"
    elif code in [61, 63, 65, 66, 67]:
        return "rain"
    elif code in [71, 73, 75, 77, 85, 86]:
        return "snow"
    elif code in [80, 81, 82]:
        return "rain showers"
    elif code in [95, 96, 99]:
        return "thunderstorm"
    else:
        return "partly cloudy"


async def fetch_real_weather(city: str, request, logger=None) -> Optional[WeatherData]:
    """Fetch real weather data from Open-Meteo API."""

    if logger:
        logger.debug(f"Fetching forecast for {city}, duration: {request.duration_days} days")
    try:
        trip_start = request.start_date
        trip_end = getattr(request, "end_date", None)
        if trip_end is None and trip_start is not None:
            trip_end = trip_start + timedelta(days=max(0, request.duration_days - 1))

        if logger:
            logger.debug(f"Trip dates: {trip_start} → {trip_end} ({request.duration_days} days)")

        forecast_data = await weather_client.get_forecast(
            city=city,
            days=request.duration_days,
            start_date=trip_start,
            end_date=trip_end,
        )

        if not forecast_data:
            if logger:
                logger.warning("Weather API returned no data")
            return None

        daily = forecast_data.get("daily", {})
        location = forecast_data.get("location", {})

        if not daily or not daily.get("time"):
            return None

        dates = daily.get("time", [])
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        temps_mean = daily.get("temperature_2m_mean", [])
        precip_sums = daily.get("precipitation_sum", [])
        precip_probs = daily.get("precipitation_probability_max", [])
        weather_codes = daily.get("weathercode", [])
        wind_speeds = daily.get("windspeed_10m_max", [])
        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])

        forecasts = []
        for i in range(min(len(dates), request.duration_days)):
            forecast_date = datetime.fromisoformat(dates[i]).date()

            temp_max = temps_max[i] if i < len(temps_max) else 25.0
            temp_min = temps_min[i] if i < len(temps_min) else 15.0
            temp_avg = temps_mean[i] if i < len(temps_mean) else 20.0
            precip_mm = precip_sums[i] if i < len(precip_sums) else 0.0

            if i < len(precip_probs) and precip_probs[i] is not None:
                precip_prob = precip_probs[i] / 100.0
            else:
                if precip_mm > 2.0:
                    precip_prob = 0.70
                elif precip_mm > 0.5:
                    precip_prob = 0.35
                else:
                    precip_prob = 0.05

            weather_code = weather_codes[i] if i < len(weather_codes) else 0
            condition = weather_code_to_condition(weather_code)
            wind_speed = wind_speeds[i] if i < len(wind_speeds) else 10.0

            try:
                sunrise_dt = datetime.fromisoformat(sunrises[i]) if i < len(sunrises) else None
                sunset_dt = datetime.fromisoformat(sunsets[i]) if i < len(sunsets) else None
                sunrise_time = sunrise_dt.time() if sunrise_dt else time(6, 30)
                sunset_time = sunset_dt.time() if sunset_dt else time(20, 30)
            except Exception:
                sunrise_time = time(6, 30)
                sunset_time = time(20, 30)

            is_good = (
                condition in ["clear", "partly cloudy", "overcast"]
                and precip_prob < 0.4
                and precip_mm < 5.0
                and temp_min > 5
                and temp_max < 35
                and wind_speed < 40
            )

            forecasts.append(
                DailyForecast(
                    date=forecast_date,
                    temp_min=temp_min,
                    temp_max=temp_max,
                    temp_avg=temp_avg,
                    condition=condition,
                    precipitation_probability=precip_prob,
                    precipitation_mm=precip_mm,
                    wind_speed_kmh=wind_speed,
                    humidity_percent=60.0,
                    sunrise=sunrise_time,
                    sunset=sunset_time,
                    is_good_for_outdoor=is_good,
                )
            )

        risk_assessment = assess_weather_risks(forecasts)
        destination_name = location.get("name", city)
        if location.get("country"):
            destination_name = f"{destination_name}, {location['country']}"

        return WeatherData(destination=destination_name, forecasts=forecasts, risk_assessment=risk_assessment)

    except Exception as e:
        if logger:
            logger.error(f"Error fetching real weather: {type(e).__name__}: {e}")
        return None


def assess_weather_risks(forecasts: List[DailyForecast]) -> WeatherRisk:
    """Assess weather risks from forecast data."""
    rain_days = sum(1 for f in forecasts if f.precipitation_probability > 0.5)
    extreme_temp_days = sum(1 for f in forecasts if f.temp_max > 35 or f.temp_min < 5)

    if rain_days > len(forecasts) // 2:
        overall_risk = "high"
    elif rain_days > 1:
        overall_risk = "medium"
    else:
        overall_risk = "low"

    recommendations = []
    if rain_days > 0:
        recommendations.append("Pack an umbrella and rain jacket")
    if any(f.temp_max > 30 for f in forecasts):
        recommendations.append("Bring sun protection and stay hydrated")
    if all(f.is_good_for_outdoor for f in forecasts):
        recommendations.append("Perfect weather for outdoor activities!")

    indoor_days = [f.date for f in forecasts if not f.is_good_for_outdoor]

    return WeatherRisk(
        overall_risk=overall_risk,
        rain_risk_days=rain_days,
        extreme_temp_days=extreme_temp_days,
        storm_probability=0.1 if rain_days > 2 else 0.0,
        recommendations=recommendations,
        indoor_recommended_days=indoor_days,
    )


def generate_fallback_weather(request) -> WeatherData:
    """Generate fallback weather data when API is unavailable."""
    from datetime import date as date_cls

    if not request.start_date:
        current_date = date_cls.today() + timedelta(days=30)
    else:
        current_date = request.start_date

    forecasts = []
    for day in range(request.duration_days):
        forecast_date = current_date + timedelta(days=day)
        is_good_day = day % 4 != 0

        if is_good_day:
            condition = "sunny" if day % 2 == 0 else "partly cloudy"
            temp_min = 18.0 + day * 0.5
            temp_max = 25.0 + day * 0.5
            precip_prob = 0.1
            precip_mm = 0.0
        else:
            condition = "rainy"
            temp_min = 15.0
            temp_max = 20.0
            precip_prob = 0.7
            precip_mm = 5.0

        forecasts.append(
            DailyForecast(
                date=forecast_date,
                temp_min=temp_min,
                temp_max=temp_max,
                temp_avg=(temp_min + temp_max) / 2,
                condition=condition,
                precipitation_probability=precip_prob,
                precipitation_mm=precip_mm,
                wind_speed_kmh=10.0 + day * 2,
                humidity_percent=60.0,
                sunrise=time(6, 30),
                sunset=time(20, 30),
                is_good_for_outdoor=is_good_day,
            )
        )

    risk_assessment = assess_weather_risks(forecasts)
    return WeatherData(destination=request.destination, forecasts=forecasts, risk_assessment=risk_assessment)
