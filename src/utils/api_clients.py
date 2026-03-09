"""
API Integration Utilities - Real-time API clients for external services.
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger("trip_planner.api_clients")


class AmadeusClient:
    """
    Amadeus API client for flight searches.
    Documentation: https://developers.amadeus.com/
    """
    
    BASE_URL = "https://test.api.amadeus.com"  # Use production: https://api.amadeus.com
    
    def __init__(self):
        self.api_key = settings.amadeus_api_key
        self.api_secret = settings.amadeus_api_secret
        self._access_token = None
        self._token_expires_at = None
    
    async def _get_access_token(self) -> str:
        """Get or refresh OAuth access token."""
        
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 1799)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                return self._access_token
            else:
                raise Exception(f"Failed to get Amadeus token: {response.text}")
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for flight offers.
        
        Args:
            origin: IATA code (e.g., "JFK")
            destination: IATA code (e.g., "CDG")
            departure_date: Date in YYYY-MM-DD format
            adults: Number of adult passengers
            max_results: Maximum number of results
            
        Returns:
            List of flight offers
        """
        
        if not self.api_key or not self.api_secret:
            logger.warning("Amadeus API credentials not configured")
            return []
        
        try:
            token = await self._get_access_token()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/v2/shopping/flight-offers",
                    params={
                        "originLocationCode": origin,
                        "destinationLocationCode": destination,
                        "departureDate": departure_date,
                        "adults": adults,
                        "max": max_results,
                        "currencyCode": "USD",
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Amadeus API error: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching flights: {type(e).__name__}: {str(e)}")
            return []
    
    async def search_hotels_by_city(
        self,
        city_code: str,
        check_in_date: str,
        check_out_date: str,
        adults: int = 1,
        radius: int = 20,
        radius_unit: str = "KM",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for hotels in a city.
        
        Args:
            city_code: IATA city code (e.g., "PAR" for Paris, "NYC" for New York)
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            adults: Number of adults
            radius: Search radius
            radius_unit: Unit (KM or MILE)
            max_results: Maximum number of results
            
        Returns:
            List of hotel offers with pricing
        """
        
        if not self.api_key or not self.api_secret:
            logger.warning("Amadeus API credentials not configured")
            return []
        
        try:
            token = await self._get_access_token()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/v3/shopping/hotel-offers",
                    params={
                        "cityCode": city_code,
                        "checkInDate": check_in_date,
                        "checkOutDate": check_out_date,
                        "adults": adults,
                        "radius": radius,
                        "radiusUnit": radius_unit,
                        "paymentPolicy": "NONE",
                        "includeClosed": False,
                        "bestRateOnly": True,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    hotels = data.get("data", [])
                    logger.info(f"Found {len(hotels)} hotels in {city_code}")
                    return hotels[:max_results]
                else:
                    logger.error(f"Amadeus Hotels API error: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching hotels: {type(e).__name__}: {str(e)}")
            return []
    
    async def search_poi(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5,
        categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for Points of Interest using Amadeus Tours and Activities API.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius: Search radius in kilometers (max 20)
            categories: List of category codes (optional)
            
        Available categories:
        - SIGHTS: Sightseeing & Landmarks
        - NATURE_AND_PARKS: Nature & Parks
        - SHOWS_AND_ENTERTAINMENT: Shows & Entertainment
        - NIGHTLIFE: Nightlife
        - SHOPPING: Shopping
        - RESTAURANTS: Restaurants
        - MUSEUMS: Museums
        
        Returns:
            List of POI (attractions, activities, tours)
        """
        
        if not self.api_key or not self.api_secret:
            logger.warning("Amadeus API credentials not configured")
            return []
        
        try:
            token = await self._get_access_token()
            
            # Build query parameters
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "radius": min(radius, 20),  # Max 20km
            }
            
            # Add categories if specified
            if categories:
                params["categories"] = ",".join(categories)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/v1/shopping/activities",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=20.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    activities = data.get("data", [])
                    logger.info(f"Found {len(activities)} POIs via Amadeus")
                    return activities
                elif response.status_code == 404:
                    logger.info("No POIs found in this location via Amadeus")
                    return []
                else:
                    logger.warning(f"Amadeus POI API returned {response.status_code}: {response.text[:200]}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching Amadeus POI: {type(e).__name__}: {str(e)}")
            return []
    
    def get_city_code_from_name(self, city_name: str) -> str:
        """
        Map city names to IATA codes for Amadeus Hotel Search API.
        Common city codes for hotel search.
        """
        city_mapping = {
            # Europe
            "paris": "PAR", "london": "LON", "rome": "ROM", "barcelona": "BCN",
            "amsterdam": "AMS", "berlin": "BER", "madrid": "MAD", "vienna": "VIE",
            "prague": "PRG", "lisbon": "LIS", "dublin": "DUB", "athens": "ATH",
            "venice": "VCE", "florence": "FLR", "milan": "MIL", "naples": "NAP",
            "brussels": "BRU", "copenhagen": "CPH", "stockholm": "STO", "oslo": "OSL",
            "helsinki": "HEL", "budapest": "BUD", "warsaw": "WAW", "krakow": "KRK",
            "zurich": "ZRH", "geneva": "GVA", "edinburgh": "EDI", "manchester": "MAN",
            "munich": "MUC", "hamburg": "HAM", "frankfurt": "FRA", "nice": "NCE",
            # North America
            "new york": "NYC", "los angeles": "LAX", "chicago": "CHI", "miami": "MIA",
            "san francisco": "SFO", "las vegas": "LAS", "seattle": "SEA", "boston": "BOS",
            "toronto": "YTO", "vancouver": "YVR", "montreal": "YMQ", "calgary": "YYC",
            "washington": "WAS", "philadelphia": "PHL", "denver": "DEN", "atlanta": "ATL",
            "orlando": "ORL", "phoenix": "PHX", "san diego": "SAN", "portland": "PDX",
            "austin": "AUS", "nashville": "BNA", "new orleans": "MSY",
            # Asia
            "tokyo": "TYO", "singapore": "SIN", "hong kong": "HKG", "bangkok": "BKK",
            "dubai": "DXB", "shanghai": "SHA", "beijing": "BJS", "seoul": "SEL",
            "mumbai": "BOM", "delhi": "DEL", "osaka": "OSA", "kuala lumpur": "KUL",
            "taipei": "TPE", "manila": "MNL", "jakarta": "JKT", "ho chi minh": "SGN",
            "hanoi": "HAN", "phuket": "HKT", "bali": "DPS", "chiang mai": "CNX",
            "istanbul": "IST", "doha": "DOH", "abu dhabi": "AUH", "riyadh": "RUH",
            # Oceania
            "sydney": "SYD", "melbourne": "MEL", "auckland": "AKL", "brisbane": "BNE",
            "perth": "PER", "wellington": "WLG", "queenstown": "ZQN",
            # South America
            "sao paulo": "SAO", "rio de janeiro": "RIO", "buenos aires": "BUE",
            "lima": "LIM", "bogota": "BOG", "santiago": "SCL", "cartagena": "CTG",
            "quito": "UIO", "cusco": "CUZ", "montevideo": "MVD",
            # Africa & Middle East
            "cairo": "CAI", "cape town": "CPT", "johannesburg": "JNB", "marrakech": "RAK",
            "casablanca": "CAS", "nairobi": "NBO", "tel aviv": "TLV", "jerusalem": "JRS",
        }
        
        city_lower = city_name.lower().strip()
        return city_mapping.get(city_lower, city_name[:3].upper())


class OpenMeteoClient:
    """
    Open-Meteo API client for weather data.
    Documentation: https://open-meteo.com/en/docs
    
    Open-Meteo is a free weather API with no API key required.
    Features:
    - Up to 16 days forecast
    - 10,000 requests per day
    - No authentication needed
    """
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_HORIZON_DAYS = 16  # Open-Meteo max forecast window

    def __init__(self):
        pass  # No API key needed!
    
    async def _geocode_city(self, city: str) -> Optional[Dict[str, float]]:
        """
        Convert city name to coordinates using Open-Meteo geocoding.
        
        Args:
            city: City name
            
        Returns:
            Dict with latitude and longitude, or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.GEOCODING_URL,
                    params={
                        "name": city,
                        "count": 1,
                        "language": "en",
                        "format": "json"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("results"):
                        result = data["results"][0]
                        return {
                            "latitude": result["latitude"],
                            "longitude": result["longitude"],
                            "name": result.get("name", city),
                            "country": result.get("country", "")
                        }
                return None
                
        except Exception as e:
            logger.error(f"Error geocoding city: {type(e).__name__}: {str(e)}")
            return None
    
    async def get_forecast(
        self,
        city: str,
        days: int = 7,
        start_date=None,   # datetime.date — first day of trip
        end_date=None,     # datetime.date — last day of trip
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather data for a city and specific trip dates.

        Strategy:
        - Trip starts within the next 16 days  → Open-Meteo Forecast API
          (real forecast with start_date / end_date params)
        - Trip starts more than 16 days ahead  → Open-Meteo Archive API
          using the equivalent dates from last year as a seasonal climate
          proxy (same month/day, year - 1). This gives realistic temperatures
          and conditions for the destination at that time of year.

        Args:
            city: City name
            days: Number of days (used when start_date is not provided)
            start_date: First day of the trip (datetime.date)
            end_date: Last day of the trip (datetime.date)

        Returns:
            Weather data dict in Open-Meteo format
        """
        from datetime import date as _date, timedelta as _td
        try:
            today = _date.today()

            # Resolve start / end dates
            if start_date is None:
                start_date = today
            if end_date is None:
                end_date = start_date + _td(days=max(0, days - 1))

            # Ensure they are date objects (not datetime)
            if hasattr(start_date, 'date'):
                start_date = start_date.date()
            if hasattr(end_date, 'date'):
                end_date = end_date.date()

            days_until_start = (start_date - today).days

            # Geocode city
            location = await self._geocode_city(city)
            if not location:
                logger.error(f"Could not find coordinates for city: {city}")
                return None

            base_params = {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "timezone": "auto",
            }

            if days_until_start <= self.FORECAST_HORIZON_DAYS:
                # ── CASE 1: Near future — use real forecast ──────────────────
                # Clamp dates within the forecast window
                api_start = max(start_date, today)
                api_end = min(end_date, today + _td(days=self.FORECAST_HORIZON_DAYS - 1))
                params = {
                    **base_params,
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
                        "precipitation_sum,precipitation_probability_max,"
                        "weathercode,windspeed_10m_max,sunrise,sunset"
                    ),
                    "start_date": api_start.isoformat(),
                    "end_date": api_end.isoformat(),
                }
                url = self.BASE_URL
                logger.info(
                    f"Weather: using FORECAST API for {city} "
                    f"{api_start} → {api_end}"
                )
            else:
                # ── CASE 2: Far future — use last year's archive as proxy ────
                try:
                    proxy_start = start_date.replace(year=start_date.year - 1)
                except ValueError:
                    # Feb 29 in a leap year → use Feb 28
                    proxy_start = start_date.replace(year=start_date.year - 1, day=28)
                try:
                    proxy_end = end_date.replace(year=end_date.year - 1)
                except ValueError:
                    proxy_end = end_date.replace(year=end_date.year - 1, day=28)

                params = {
                    **base_params,
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
                        "precipitation_sum,weather_code,windspeed_10m_max,"
                        "sunrise,sunset"
                    ),
                    "start_date": proxy_start.isoformat(),
                    "end_date": proxy_end.isoformat(),
                }
                url = self.ARCHIVE_URL
                logger.info(
                    f"Weather: trip is {days_until_start} days away — "
                    f"using ARCHIVE API proxy {proxy_start} → {proxy_end} "
                    f"(last year, same season)"
                )

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)

                if response.status_code == 200:
                    data = response.json()
                    data["location"] = location
                    # Normalise weather_code → weathercode so the parser
                    # always finds the same key regardless of which API was used
                    if "daily" in data and "weather_code" in data["daily"]:
                        data["daily"]["weathercode"] = data["daily"].pop("weather_code")
                    return data
                else:
                    logger.error(
                        f"Open-Meteo API error {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error fetching weather: {type(e).__name__}: {str(e)}")
            return None


class FreePlacesClient:
    """
    Places API client using Amadeus Tours & Activities API exclusively.
    
    Features:
    - Amadeus Tours & Activities: Production-grade POI data (2000 requests/month free)
    - Includes attractions, museums, restaurants, parks, shopping, and nightlife
    - Provides ratings, descriptions, pricing, and location data
    - Nominatim: Geocoding for city coordinates (1 req/sec, no key needed)
    
    All services are completely free with no billing required!
    """
    
    FOURSQUARE_URL = "https://api.foursquare.com/v3/places"
    OPENTRIPMAP_URL = "https://api.opentripmap.com/0.1/en/places"
    # Multiple Overpass servers for redundancy
    OVERPASS_SERVERS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]
    NOMINATIM_URL = "https://nominatim.openstreetmap.org"
    
    def __init__(self):
        self.foursquare_key = settings.foursquare_api_key  # Free key from foursquare.com
        self.opentripmap_key = settings.opentripmap_api_key  # Free key from opentripmap.io
        self.user_agent = "TripPlannerApp/1.0"  # Required for Nominatim
        self.current_overpass_server = 0  # Track which server to use
    
    async def geocode_city(self, city: str) -> Optional[Dict[str, Any]]:
        """Geocode city name to coordinates using Nominatim."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.NOMINATIM_URL}/search",
                    params={
                        "q": city,
                        "format": "json",
                        "limit": 1
                    },
                    headers={"User-Agent": self.user_agent},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return {
                            "lat": float(data[0]["lat"]),
                            "lon": float(data[0]["lon"]),
                            "name": data[0].get("display_name", city)
                        }
                return None
                
        except Exception as e:
            logger.error(f"Error geocoding city: {type(e).__name__}: {str(e)}")
            return None
    
    async def search_nearby(
        self,
        location: str,
        radius: int = 5000,
        type_: str = "tourist_attraction",
        keyword: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search for nearby places using Amadeus API only.
        
        Args:
            location: Lat,lng coordinates (e.g., "48.8566,2.3522")
            radius: Search radius in meters
            type_: Place type
            keyword: Search keyword
            
        Returns:
            List of places in Google Places-compatible format
        """
        
        lat, lon = location.split(",")
        lat, lon = float(lat), float(lon)
        
        # Use Amadeus API exclusively (production-grade travel data)
        try:
            results = await self._search_amadeus(lat, lon, radius, type_)
            if results:
                logger.info(f"Amadeus returned {len(results)} places for {type_}")
                return results
            else:
                logger.warning(f"Amadeus returned no results for {type_} at {lat},{lon}")
                return []
        except Exception as e:
            logger.error(f"Amadeus search failed: {type(e).__name__}: {str(e)}")
            return []
    
    async def _search_amadeus(
        self, lat: float, lon: float, radius: int, type_: str
    ) -> List[Dict[str, Any]]:
        """
        Search places using Amadeus Tours and Activities API.
        Production-grade travel data.
        """
        
        try:
            # Map type to Amadeus categories
            categories = self._map_type_to_amadeus_categories(type_)
            
            # Use the global amadeus_client
            activities = await amadeus_client.search_poi(
                latitude=lat,
                longitude=lon,
                radius=int(radius / 1000),  # Convert meters to kilometers
                categories=categories
            )
            
            if activities:
                return self._format_amadeus_results(activities)
            return []
            
        except Exception as e:
            logger.error(f"Error searching Amadeus: {type(e).__name__}: {str(e)}")
            return []
    
    def _map_type_to_amadeus_categories(self, type_: str) -> Optional[List[str]]:
        """Map Google Places types to Amadeus activity categories."""
        mapping = {
            "tourist_attraction": ["SIGHTS"],
            "museum": ["MUSEUMS"],
            "park": ["NATURE_AND_PARKS"],
            "restaurant": ["RESTAURANTS"],
            "shopping_mall": ["SHOPPING"],
            "nightlife": ["NIGHTLIFE"],
        }
        return mapping.get(type_)
    
    def _format_amadeus_results(self, activities: List[Dict]) -> List[Dict[str, Any]]:
        """Format Amadeus activity results to Google Places-compatible format."""
        
        results = []
        
        for activity in activities:
            try:
                # Extract basic info
                activity_id = activity.get("id", "")
                name = activity.get("name", "Unnamed")
                
                # Get location (convert strings to float)
                geo_code = activity.get("geoCode", {})
                try:
                    lat = float(geo_code.get("latitude", 0))
                    lon = float(geo_code.get("longitude", 0))
                except (ValueError, TypeError):
                    lat, lon = 0.0, 0.0
                
                # Get rating (convert string to float)
                rating_raw = activity.get("rating", 4.0)
                try:
                    rating = float(rating_raw) if rating_raw else 4.0
                except (ValueError, TypeError):
                    rating = 4.0
                
                # Get price
                price_info = activity.get("price", {})
                price_amount = price_info.get("amount", 0)
                
                # Get pictures count as a proxy for popularity
                pictures = activity.get("pictures", [])
                popularity = len(pictures) * 50 + 100  # Rough estimate
                
                # Get description
                description = activity.get("shortDescription", "")
                
                # Calculate price level (convert string to float if needed)
                price_level = 0
                if price_amount:
                    try:
                        price_value = float(price_amount) if isinstance(price_amount, str) else price_amount
                        price_level = min(4, int(price_value / 20))
                    except (ValueError, TypeError):
                        price_level = 0
                
                result = {
                    "place_id": f"amadeus_{activity_id}",
                    "name": name,
                    "geometry": {
                        "location": {
                            "lat": lat,
                            "lng": lon
                        }
                    },
                    "rating": min(5.0, rating),
                    "user_ratings_total": popularity,
                    "vicinity": "",
                    "types": [activity.get("category", "attraction")],
                    "price_level": price_level,
                    "description": description,
                }
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Error formatting Amadeus activity: {e}")
                continue
        
        return results
    
    async def _search_foursquare(
        self, lat: float, lon: float, radius: int, type_: str
    ) -> List[Dict[str, Any]]:
        """
        Search places using Foursquare Places API (v3).
        Production-grade data with 99,000 calls/day free tier.
        """
        
        try:
            # Map type to Foursquare categories
            category_id = self._map_type_to_foursquare_category(type_)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.FOURSQUARE_URL}/search",
                    params={
                        "ll": f"{lat},{lon}",
                        "radius": radius,
                        "categories": category_id,
                        "limit": 50,
                        "fields": "name,location,rating,popularity,price,categories,hours"
                    },
                    headers={
                        "Authorization": self.foursquare_key,
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._format_foursquare_results(data)
                elif response.status_code == 429:
                    logger.warning("Foursquare rate limit reached")
                    return []
                else:
                    logger.warning(f"Foursquare API error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching Foursquare: {type(e).__name__}: {str(e)}")
            return []
    
    def _map_type_to_foursquare_category(self, type_: str) -> str:
        """Map Google Places types to Foursquare category IDs."""
        # Foursquare category IDs: https://developer.foursquare.com/docs/categories
        mapping = {
            "tourist_attraction": "16000",  # Landmarks and Outdoors
            "museum": "10027",  # Museum
            "park": "16032",  # Park
            "restaurant": "13065",  # Restaurant
            "shopping_mall": "17000",  # Retail
        }
        return mapping.get(type_, "16000")  # Default to Landmarks
    
    def _format_foursquare_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Format Foursquare results to Google Places-like format."""
        
        results = []
        places = data.get("results", [])
        
        for place in places:
            # Extract location
            location = place.get("geocodes", {}).get("main", {})
            lat = location.get("latitude", 0)
            lng = location.get("longitude", 0)
            
            if not lat or not lng:
                continue
            
            # Extract address
            address_parts = []
            address = place.get("location", {})
            if address.get("address"):
                address_parts.append(address["address"])
            if address.get("locality"):
                address_parts.append(address["locality"])
            vicinity = ", ".join(address_parts) if address_parts else ""
            
            # Extract rating (Foursquare uses 0-10 scale, convert to 0-5)
            rating = place.get("rating", 0)
            if rating > 5:
                rating = rating / 2.0  # Convert 0-10 to 0-5
            
            # Extract popularity (0-1 scale, convert to reviews count estimate)
            popularity = place.get("popularity", 0)
            estimated_reviews = int(popularity * 1000) if popularity else 100
            
            # Extract price level (1-4)
            price = place.get("price", 2)  # Default to moderate
            
            # Extract categories
            categories = place.get("categories", [])
            types = [cat.get("name", "").lower() for cat in categories] if categories else ["place"]
            
            # Build result in Google Places format
            result = {
                "place_id": f"fsq_{place.get('fsq_id', '')}",
                "name": place.get("name", "Unnamed"),
                "geometry": {
                    "location": {
                        "lat": lat,
                        "lng": lng
                    }
                },
                "rating": min(5.0, rating),  # Cap at 5.0
                "user_ratings_total": estimated_reviews,
                "vicinity": vicinity,
                "types": types,
                "price_level": price,
                # Additional Foursquare-specific data
                "popularity": place.get("popularity", 0),
                "verified": place.get("verified", False),
            }
            results.append(result)
        
        return results
    
    async def _search_opentripmap(
        self, lat: float, lon: float, radius: int, type_: str
    ) -> List[Dict[str, Any]]:
        """Search tourist attractions using OpenTripMap (optional - falls back to Overpass)."""
        
        if not self.opentripmap_key:
            logger.info("OpenTripMap not configured - using Overpass API (works great!)")
            return await self._search_overpass(lat, lon, radius, type_)
        
        try:
            # Convert radius to search box
            radius_km = radius / 1000.0
            
            async with httpx.AsyncClient() as client:
                # Search for places within radius
                response = await client.get(
                    f"{self.OPENTRIPMAP_URL}/radius",
                    params={
                        "radius": int(radius),
                        "lon": lon,
                        "lat": lat,
                        "kinds": self._map_type_to_otm_kinds(type_),
                        "format": "json",
                        "limit": 50,
                        "apikey": self.opentripmap_key
                    },
                    timeout=20.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._format_otm_results(data)
                else:
                    logger.warning(f"OpenTripMap API error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching OpenTripMap: {type(e).__name__}: {str(e)}")
            return []
    
    async def _search_overpass(
        self, lat: float, lon: float, radius: int, type_: str
    ) -> List[Dict[str, Any]]:
        """Search POIs using Overpass API (OpenStreetMap) with retry logic."""
        
        # Build Overpass QL query - simplified for faster execution
        osm_tags = self._map_type_to_osm_tags(type_)
        
        # Simplified query: search nodes only (faster than nodes+ways)
        # Reduced timeout from 25s to 8s for faster failures
        query = f"""
        [out:json][timeout:8];
        node{osm_tags}(around:{radius},{lat},{lon});
        out 20;
        """
        
        # Retry configuration - reduced retries for faster fallback
        max_retries = 2  # Reduced from 3 to 2
        base_delay = 0.5  # Start with 0.5 second delay
        
        for attempt in range(max_retries):
            try:
                # Try each Overpass server in rotation
                server_url = self.OVERPASS_SERVERS[self.current_overpass_server % len(self.OVERPASS_SERVERS)]
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        server_url,
                        data={"data": query},
                        timeout=10.0  # Reduced to 10s for faster failure
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = self._format_osm_results(data)
                        
                        # Add delay between successful requests to be respectful
                        if results:
                            await asyncio.sleep(0.5)  # 500ms delay
                        
                        return results
                    
                    elif response.status_code == 504:
                        # Gateway timeout - try next server or retry
                        print(f"Overpass API error: 504 (attempt {attempt + 1}/{max_retries})")
                        logger.warning(f"Overpass timeout on {server_url}, attempt {attempt + 1}")
                        
                        # Switch to next server
                        self.current_overpass_server = (self.current_overpass_server + 1) % len(self.OVERPASS_SERVERS)
                        
                        # Exponential backoff: wait longer each retry
                        if attempt < max_retries - 1:
                            delay = base_delay * (1.5 ** attempt)  # 0.5s, 0.75s (faster)
                            logger.info(f"Waiting {delay}s before retry...")
                            await asyncio.sleep(delay)
                        continue
                    
                    elif response.status_code == 429:
                        # Rate limited - wait longer
                        logger.warning(f"Overpass rate limit hit, waiting...")
                        await asyncio.sleep(5)
                        continue
                    
                    else:
                        logger.error(f"Overpass API error: {response.status_code}")
                        return []
                        
            except httpx.TimeoutException:
                logger.warning(f"Overpass request timeout (attempt {attempt + 1}/{max_retries})")
                # Switch server on timeout
                self.current_overpass_server = (self.current_overpass_server + 1) % len(self.OVERPASS_SERVERS)
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                continue
                
            except Exception as e:
                logger.error(f"Error searching Overpass: {type(e).__name__}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay)
                    continue
                return []
        
        # All retries exhausted
        logger.error(f"Overpass API failed after {max_retries} attempts")
        return []
    
    def _map_type_to_otm_kinds(self, type_: str) -> str:
        """Map Google Places types to OpenTripMap kinds."""
        mapping = {
            "tourist_attraction": "interesting_places,tourist_facilities",
            "museum": "museums",
            "park": "natural",
            "restaurant": "foods",
            "shopping_mall": "shops",
        }
        return mapping.get(type_, "interesting_places")
    
    def _map_type_to_osm_tags(self, type_: str) -> str:
        """Map Google Places types to OSM tags."""
        mapping = {
            "tourist_attraction": '["tourism"~"attraction|viewpoint|museum|artwork|gallery|theme_park"]',
            "museum": '["tourism"="museum"]',
            "park": '["leisure"~"park|garden|nature_reserve"]',
            "restaurant": '["amenity"~"restaurant|cafe|bar"]',
            "shopping_mall": '["shop"~"mall|department_store"]',
        }
        return mapping.get(type_, '["tourism"]')
    
    def _format_otm_results(self, data) -> List[Dict[str, Any]]:
        """Format OpenTripMap results to Google Places-like format."""
        
        results = []
        
        # Handle different response formats
        if isinstance(data, dict):
            # If data is a dict, try to extract the features/items list
            items = data.get('features', data.get('items', data.get('results', [])))
            # If still nothing, data itself might need to be wrapped
            if not items and 'name' in data:
                items = [data]
            elif not items:
                logger.warning(f"Unexpected OpenTripMap data format: {type(data)}")
                return []
        elif isinstance(data, list):
            items = data
        else:
            logger.error(f"Invalid OpenTripMap data type: {type(data)}")
            return []
        
        for item in items:
            # Skip if item is not a dict
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item in OpenTripMap results: {type(item)}")
                continue
                
            if not item.get("name"):
                continue
            
            result = {
                "place_id": f"otm_{item.get('xid', item.get('name', ''))}",
                "name": item.get("name", "Unnamed"),
                "geometry": {
                    "location": {
                        "lat": item.get("point", {}).get("lat", 0),
                        "lng": item.get("point", {}).get("lon", 0)
                    }
                },
                "rating": 4.0,  # OpenTripMap doesn't provide ratings
                "user_ratings_total": 100,  # Estimate
                "vicinity": "",
                "types": [item.get("kinds", "attraction").split(",")[0]],
            }
            results.append(result)
        
        return results
    
    def _format_osm_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Format OSM/Overpass results to Google Places-like format."""
        
        results = []
        
        # Validate data format
        if not isinstance(data, dict):
            logger.error(f"Invalid OSM data type: {type(data)}")
            return []
        
        elements = data.get("elements", [])
        
        if not isinstance(elements, list):
            logger.error(f"Invalid OSM elements type: {type(elements)}")
            return []
        
        for element in elements:
            # Skip if element is not a dict
            if not isinstance(element, dict):
                logger.warning(f"Skipping non-dict element in OSM results: {type(element)}")
                continue
            tags = element.get("tags", {})
            name = tags.get("name")
            
            if not name:
                continue
            
            # Get coordinates
            if element.get("lat") and element.get("lon"):
                lat, lon = element["lat"], element["lon"]
            elif element.get("center"):
                lat, lon = element["center"]["lat"], element["center"]["lon"]
            else:
                continue
            
            # Estimate rating from OSM data quality and type
            rating = 3.8  # Base rating
            tourism_type = tags.get("tourism", "")
            
            # Higher ratings for popular attraction types
            if tourism_type in ["museum", "gallery", "theme_park"]:
                rating = 4.3
            elif tourism_type in ["attraction", "viewpoint", "artwork"]:
                rating = 4.1
            elif tags.get("historic") in ["monument", "castle", "ruins"]:
                rating = 4.2
            elif tags.get("leisure") in ["park", "garden", "nature_reserve"]:
                rating = 4.0
            elif tags.get("amenity") == "restaurant":
                rating = 3.9
            
            # Bonus for heritage sites
            if tags.get("heritage") or tags.get("unesco"):
                rating += 0.3
            
            # Estimate popularity from OSM metadata
            popularity = 100  # Base
            if tags.get("wikipedia") or tags.get("wikidata"):
                popularity = 500  # Has Wikipedia page = more popular
            if tourism_type in ["museum", "theme_park"]:
                popularity = 300
            
            result = {
                "place_id": f"osm_{element.get('type', 'node')}_{element.get('id')}",
                "name": name,
                "geometry": {
                    "location": {
                        "lat": lat,
                        "lng": lon
                    }
                },
                "rating": min(5.0, rating),  # Cap at 5.0
                "user_ratings_total": popularity,
                "vicinity": tags.get("addr:street", tags.get("addr:city", "")),
                "types": [tourism_type or tags.get("amenity") or tags.get("leisure") or tags.get("historic") or "place"],
                "opening_hours": tags.get("opening_hours"),
                # Additional useful info from OSM
                "website": tags.get("website"),
                "phone": tags.get("phone"),
                "wikipedia": tags.get("wikipedia"),
            }
            results.append(result)
        
        return results
    
    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a place."""
        
        # For free APIs, details are limited
        # Can be extended with Wikipedia API integration for descriptions
        logger.info(f"Place details limited for free APIs: {place_id}")
        return None


class BookingComClient:
    """
    Booking.com API client for accommodation searches.
    Note: This uses web scraping as Booking.com API has limited access.
    For production, consider using RapidAPI or similar services.
    """
    
    def __init__(self):
        pass
    
    async def search_hotels(
        self,
        city: str,
        checkin_date: str,
        checkout_date: str,
        adults: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search for hotels (placeholder - requires proper API access).
        
        For production:
        - Use Booking.com Partner API (requires approval)
        - Or use RapidAPI's Booking.com API
        - Or use Hotels.com API
        """
        
        logger.warning("Booking.com API integration pending - requires API approval")
        logger.info(f"Would search hotels in {city} for {checkin_date} to {checkout_date}")
        
        # Return empty for now - implement with proper API access
        return []


class SerpAPIClient:
    """
    SerpAPI client for real-world travel data via Google search engines.

    Engines used:
    - google_flights  → real flight prices & schedules (works for India ✅)
    - google_hotels   → real hotel listings & prices (works for India ✅)
    - google_maps     → real attractions, POIs, restaurants (works globally ✅)

    Free tier: 100 searches / month
    Docs: https://serpapi.com/
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        self.api_key = settings.serpapi_key

    def _has_key(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def search_flights(
        self,
        origin_iata: str,
        destination_iata: str,
        outbound_date: str,          # YYYY-MM-DD
        return_date: str = "",        # YYYY-MM-DD, empty for one-way
        adults: int = 1,
        currency: str = "USD",
    ) -> Dict[str, Any]:
        """
        Search flights via Google Flights engine.
        Returns the raw SerpAPI response dict (best_flights + other_flights).
        """
        if not self._has_key():
            logger.warning("SerpAPI key not configured — skipping flight search")
            return {}

        params = {
            "engine": "google_flights",
            "departure_id": origin_iata,
            "arrival_id": destination_iata,
            "outbound_date": outbound_date,
            "currency": currency,
            "hl": "en",
            "adults": adults,
            "api_key": self.api_key,
        }
        if return_date:
            params["return_date"] = return_date

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        f"SerpAPI flights: {len(data.get('best_flights', []))} best + "
                        f"{len(data.get('other_flights', []))} other results"
                    )
                    return data
                else:
                    logger.warning(f"SerpAPI flights error {response.status_code}: {response.text[:200]}")
                    return {}
        except Exception as e:
            logger.error(f"SerpAPI flights exception: {type(e).__name__}: {e}")
            return {}

    async def search_hotels(
        self,
        destination: str,
        check_in_date: str,   # YYYY-MM-DD
        check_out_date: str,  # YYYY-MM-DD
        adults: int = 1,
        currency: str = "USD",
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search hotels via Google Hotels engine.
        Returns list of hotel property dicts.
        """
        if not self._has_key():
            logger.warning("SerpAPI key not configured — skipping hotel search")
            return []

        params = {
            "engine": "google_hotels",
            "q": f"hotels in {destination}",
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "currency": currency,
            "hl": "en",
            "gl": "us",
            "api_key": self.api_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    properties = data.get("properties", [])
                    logger.info(f"SerpAPI hotels: {len(properties)} results for '{destination}'")
                    return properties[:max_results]
                else:
                    logger.warning(f"SerpAPI hotels error {response.status_code}: {response.text[:200]}")
                    return []
        except Exception as e:
            logger.error(f"SerpAPI hotels exception: {type(e).__name__}: {e}")
            return []

    async def search_attractions(
        self,
        destination: str,
        category: str = "tourist attractions",
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search attractions / POIs via Google Maps engine.
        Returns list of place result dicts.
        """
        if not self._has_key():
            logger.warning("SerpAPI key not configured — skipping attractions search")
            return []

        params = {
            "engine": "google_maps",
            "q": f"{category} in {destination}",
            "type": "search",
            "hl": "en",
            "api_key": self.api_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("local_results", [])
                    logger.info(f"SerpAPI maps: {len(results)} results for '{category} in {destination}'")
                    return results[:max_results]
                else:
                    logger.warning(f"SerpAPI maps error {response.status_code}: {response.text[:200]}")
                    return []
        except Exception as e:
            logger.error(f"SerpAPI maps exception: {type(e).__name__}: {e}")
            return []


# Global client instances
amadeus_client = AmadeusClient()
weather_client = OpenMeteoClient()
places_client = FreePlacesClient()
booking_client = BookingComClient()
serp_client = SerpAPIClient()
