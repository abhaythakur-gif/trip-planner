"""
Agent output schemas - represents the structured outputs from each specialized agent.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, date as DateType, time as TimeType


class GeoLocation(BaseModel):
    """Geographic location with coordinates."""
    latitude: float
    longitude: float
    address: str
    city: str
    country: str


class TransportOption(BaseModel):
    """A transport option (flight, train, etc.)."""
    
    id: str = Field(..., description="Unique identifier")
    type: Literal["flight", "train", "bus", "ferry"] = "flight"
    
    # Route
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    duration_minutes: int
    
    # Pricing
    price: float
    currency: str = "USD"
    
    # Details
    carrier: str
    flight_number: Optional[str] = None
    stops: int = Field(default=0, ge=0)
    cabin_class: Literal["economy", "premium_economy", "business", "first"] = "economy"
    
    # Policies
    cancellation_policy: str = Field(default="non-refundable")
    baggage_included: bool = Field(default=True)
    
    # Scoring
    score: float = Field(default=0.0, ge=0, le=100, description="Weighted score")
    
    @property
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return self.duration_minutes / 60.0


class StayOption(BaseModel):
    """An accommodation option."""
    
    id: str = Field(..., description="Unique identifier")
    name: str
    type: Literal["hotel", "hostel", "apartment", "resort", "guesthouse"] = "hotel"
    
    # Location
    location: GeoLocation
    distance_to_center_km: float = Field(..., ge=0)
    
    # Pricing
    price_per_night: float
    total_price: float
    currency: str = "USD"
    
    # Quality
    rating: float = Field(..., ge=0, le=5)
    num_reviews: int = Field(default=0, ge=0)
    
    # Amenities
    amenities: List[str] = Field(default_factory=list)
    
    # Policies
    cancellation_policy: str = Field(default="non-refundable")
    free_cancellation_until: Optional[DateType] = None
    
    # Scoring
    score: float = Field(default=0.0, ge=0, le=100, description="Weighted score")


class DailyForecast(BaseModel):
    """Weather forecast for a single day."""
    
    date: DateType
    temp_min: float = Field(..., description="Min temperature in Celsius")
    temp_max: float = Field(..., description="Max temperature in Celsius")
    temp_avg: float = Field(..., description="Average temperature")
    
    condition: str = Field(..., description="Weather condition (sunny, rainy, etc.)")
    precipitation_probability: float = Field(default=0.0, ge=0, le=1, description="Probability of rain")
    precipitation_mm: float = Field(default=0.0, ge=0, description="Expected precipitation")
    
    wind_speed_kmh: float = Field(default=0.0, ge=0)
    humidity_percent: float = Field(default=50.0, ge=0, le=100)
    
    sunrise: Optional[TimeType] = None
    sunset: Optional[TimeType] = None
    
    is_good_for_outdoor: bool = Field(default=True)


class WeatherRisk(BaseModel):
    """Weather risk assessment."""
    
    overall_risk: Literal["low", "medium", "high"]
    rain_risk_days: int = Field(default=0, ge=0)
    extreme_temp_days: int = Field(default=0, ge=0)
    storm_probability: float = Field(default=0.0, ge=0, le=1)
    
    recommendations: List[str] = Field(default_factory=list)
    indoor_recommended_days: List[DateType] = Field(default_factory=list)


class WeatherData(BaseModel):
    """Complete weather data for destination."""
    
    destination: str
    forecasts: List[DailyForecast]
    risk_assessment: WeatherRisk
    
    @property
    def outdoor_activity_days(self) -> List[DateType]:
        """Get days suitable for outdoor activities."""
        return [f.date for f in self.forecasts if f.is_good_for_outdoor]


class Attraction(BaseModel):
    """A tourist attraction or activity."""
    
    id: str
    name: str
    category: str = Field(..., description="museum, restaurant, park, landmark, etc.")
    
    # Location
    location: GeoLocation
    
    # Quality
    rating: float = Field(..., ge=0, le=5)
    num_reviews: int = Field(default=0, ge=0)
    
    # Visit details
    estimated_duration_hours: float = Field(..., gt=0)
    cost: float = Field(default=0.0, ge=0, description="Entry cost")
    
    # Characteristics
    indoor: bool = Field(default=False)
    best_time: Literal["morning", "afternoon", "evening", "any"] = "any"
    requires_booking: bool = Field(default=False)
    
    # Info
    description: str = Field(default="")
    opening_hours: Optional[str] = None
    
    # Scoring
    score: float = Field(default=0.0, ge=0, le=100)


class AttractionList(BaseModel):
    """Categorized list of attractions."""
    
    all_attractions: List[Attraction]
    top_rated: List[Attraction]
    budget_friendly: List[Attraction]
    outdoor_activities: List[Attraction]
    indoor_activities: List[Attraction]
    
    def get_by_category(self, category: str) -> List[Attraction]:
        """Get attractions by category."""
        return [a for a in self.all_attractions if a.category == category]


class Meal(BaseModel):
    """A meal in the itinerary."""
    
    type: Literal["breakfast", "lunch", "dinner", "snack"]
    location: str
    estimated_cost: float
    time: Optional[TimeType] = None


class Activity(BaseModel):
    """An activity in the itinerary."""
    
    time_start: TimeType
    time_end: TimeType
    attraction: Attraction
    travel_time_minutes: int = Field(default=0, ge=0)
    notes: List[str] = Field(default_factory=list)


class DailyItinerary(BaseModel):
    """Itinerary for a single day."""
    
    day_number: int = Field(..., ge=1)
    date: DateType
    weather: DailyForecast
    
    activities: List[Activity]
    meals: List[Meal]
    
    total_cost: float = Field(default=0.0, ge=0)
    total_walking_distance_km: float = Field(default=0.0, ge=0)
    estimated_transit_time_hours: float = Field(default=0.0, ge=0)
    
    notes: List[str] = Field(default_factory=list)
    
    @property
    def is_overloaded(self) -> bool:
        """Check if day has too many activities."""
        return len(self.activities) > 5 or self.estimated_transit_time_hours > 4


class MultiDayItinerary(BaseModel):
    """Complete multi-day itinerary."""
    
    days: List[DailyItinerary]
    total_cost: float = Field(default=0.0, ge=0)
    
    @property
    def num_days(self) -> int:
        return len(self.days)
