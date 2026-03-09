"""
Tool functions for the Attractions Agent.
Handles city coordinate lookup, attraction API searches, fallback data,
scoring, and categorisation.
"""

from typing import List, Optional

from ...schemas.agent_outputs import Attraction, AttractionList, GeoLocation
from ...utils.api_clients import serp_client, places_client

# ---------------------------------------------------------------------------
# DATA: Known-city coordinate cache
# ---------------------------------------------------------------------------
KNOWN_CITIES = {
    # Europe
    "paris": "48.8566,2.3522",
    "london": "51.5074,-0.1278",
    "rome": "41.9028,12.4964",
    "barcelona": "41.3851,2.1734",
    "amsterdam": "52.3676,4.9041",
    "berlin": "52.5200,13.4050",
    "madrid": "40.4168,-3.7038",
    "vienna": "48.2082,16.3738",
    "prague": "50.0755,14.4378",
    "lisbon": "38.7169,-9.1399",
    "athens": "37.9838,23.7275",
    "istanbul": "41.0082,28.9784",
    "budapest": "47.4979,19.0402",
    "zurich": "47.3769,8.5417",
    "brussels": "50.8503,4.3517",
    "florence": "43.7696,11.2558",
    "venice": "45.4408,12.3155",
    "milan": "45.4642,9.1900",
    # Americas
    "new york": "40.7128,-74.0060",
    "los angeles": "34.0522,-118.2437",
    "chicago": "41.8781,-87.6298",
    "miami": "25.7617,-80.1918",
    "san francisco": "37.7749,-122.4194",
    "toronto": "43.6532,-79.3832",
    "vancouver": "49.2827,-123.1207",
    "mexico city": "19.4326,-99.1332",
    "buenos aires": "-34.6037,-58.3816",
    "rio de janeiro": "-22.9068,-43.1729",
    "cancun": "21.1619,-86.8515",
    # Asia Pacific
    "tokyo": "35.6762,139.6503",
    "singapore": "1.3521,103.8198",
    "sydney": "-33.8688,151.2093",
    "melbourne": "-37.8136,144.9631",
    "bangkok": "13.7563,100.5018",
    "hong kong": "22.3193,114.1694",
    "shanghai": "31.2304,121.4737",
    "beijing": "39.9042,116.4074",
    "seoul": "37.5665,126.9780",
    "kuala lumpur": "3.1390,101.6869",
    "bali": "-8.3405,115.0920",
    "phuket": "7.8804,98.3923",
    # Middle East & Africa
    "dubai": "25.2048,55.2708",
    "abu dhabi": "24.4539,54.3773",
    "doha": "25.2854,51.5310",
    "tel aviv": "32.0853,34.7818",
    "cairo": "30.0444,31.2357",
    "cape town": "-33.9249,18.4241",
    "marrakech": "31.6295,-7.9811",
    # India
    "goa": "15.2993,74.1240",
    "mumbai": "19.0760,72.8777",
    "delhi": "28.6139,77.2090",
    "new delhi": "28.6139,77.2090",
    "bangalore": "12.9716,77.5946",
    "bengaluru": "12.9716,77.5946",
    "hyderabad": "17.3850,78.4867",
    "chennai": "13.0827,80.2707",
    "kolkata": "22.5726,88.3639",
    "jaipur": "26.9124,75.7873",
    "agra": "27.1767,78.0081",
    "varanasi": "25.3176,82.9739",
    "udaipur": "24.5854,73.7125",
    "kochi": "9.9312,76.2673",
    "rishikesh": "30.0869,78.2676",
    "amritsar": "31.6340,74.8723",
    "leh": "34.1526,77.5771",
    "srinagar": "34.0837,74.7973",
    "shimla": "31.1048,77.1734",
    "manali": "32.2396,77.1887",
    "darjeeling": "27.0360,88.2627",
    "mysore": "12.2958,76.6394",
    "mysuru": "12.2958,76.6394",
    "ooty": "11.4102,76.6950",
    "coorg": "12.3375,75.8069",
    "hampi": "15.3350,76.4600",
    "pondicherry": "11.9416,79.8083",
}


async def get_city_coordinates(city: str, logger=None) -> str:
    """
    Return lat,lon coordinates string for a given city.
    Checks KNOWN_CITIES first (instant), then falls back to live Nominatim geocoding.
    """
    city_lower = city.lower().strip()

    if city_lower in KNOWN_CITIES:
        if logger:
            logger.debug(f"Using cached coordinates for '{city}'")
        return KNOWN_CITIES[city_lower]

    if logger:
        logger.info(f"City '{city}' not in cache — calling Nominatim for live geocoding")
    try:
        result = await places_client.geocode_city(city)
        if result:
            coords = f"{result['lat']},{result['lon']}"
            if logger:
                logger.info(f"Nominatim resolved '{city}' → {coords}")
            return coords
    except Exception as e:
        if logger:
            logger.warning(f"Nominatim geocoding failed for '{city}': {e}")

    if logger:
        logger.warning(f"Could not geocode '{city}', using India centre as geographic fallback")
    return "20.5937,78.9629"


async def search_real_attractions(
    city: str, coordinates: str, constraints, logger=None
) -> List[Attraction]:
    """
    Search for real attractions using the SerpAPI Google Maps engine.
    Returns a list of Attraction objects; empty list on failure.
    """
    try:
        search_categories = [
            "tourist attractions",
            "museums and art galleries",
            "parks and nature",
            "restaurants and local food",
            "shopping markets",
        ]

        attractions: List[Attraction] = []
        seen_names: set = set()

        for category in search_categories:
            if logger:
                logger.info(f"SerpAPI: searching '{category}' in {city}")
            try:
                results = await serp_client.search_attractions(
                    destination=city,
                    category=category,
                    max_results=8,
                )
            except Exception as e:
                if logger:
                    logger.warning(f"SerpAPI call failed for '{category}': {type(e).__name__}: {e}")
                continue

            if not isinstance(results, list):
                continue

            for i, place in enumerate(results):
                try:
                    name = place.get("title") or place.get("name") or ""
                    if not name or name in seen_names:
                        continue
                    seen_names.add(name)

                    raw_rating = place.get("rating")
                    rating = float(raw_rating) if raw_rating else 4.0
                    rating = min(5.0, rating)

                    num_reviews = int(place.get("reviews") or place.get("user_ratings_total") or 100)

                    gps = place.get("gps_coordinates") or {}
                    lat = float(gps.get("latitude") or 0)
                    lon = float(gps.get("longitude") or 0)
                    address = place.get("address") or ""

                    place_type = (
                        place.get("type") or place.get("category") or category.split()[0]
                    )

                    duration_map = {
                        "museum": 2.5, "gallery": 2.0, "landmark": 1.5,
                        "park": 2.0, "nature": 2.0, "restaurant": 1.5,
                        "food": 1.5, "shopping": 2.0, "market": 1.5,
                        "tourist": 2.0,
                    }
                    cat_key = place_type.lower().split()[0] if place_type else ""
                    duration = duration_map.get(cat_key, 2.0)
                    indoor = cat_key in {"museum", "gallery", "restaurant", "food", "shopping", "market"}

                    price_str = str(place.get("price") or "")
                    cost = 0.0
                    if price_str.startswith("₹"):
                        digits = "".join(c for c in price_str if c.isdigit())
                        cost = float(digits) if digits else 0.0
                    elif price_str.startswith("$"):
                        digits = "".join(c for c in price_str if c.isdigit() or c == ".")
                        cost = float(digits) if digits else 0.0

                    description = (
                        place.get("description")
                        or place.get("snippet")
                        or f"A popular {place_type} in {city}."
                    )

                    attraction = Attraction(
                        id=f"serp_{hash(name) % 100000}",
                        name=name,
                        category=place_type,
                        location=GeoLocation(
                            latitude=lat,
                            longitude=lon,
                            address=address,
                            city=city,
                            country="",
                        ),
                        rating=rating,
                        num_reviews=num_reviews,
                        estimated_duration_hours=duration,
                        cost=cost,
                        indoor=indoor,
                        best_time="any",
                        requires_booking=cat_key == "museum",
                        description=description,
                        opening_hours=None,
                    )
                    attractions.append(attraction)

                except Exception as e:
                    if logger:
                        logger.warning(f"Error parsing SerpAPI attraction: {e}")
                    continue

        if logger:
            logger.info(f"SerpAPI returned {len(attractions)} attractions for {city}")
        return attractions

    except Exception as e:
        if logger:
            logger.error(f"Error in search_real_attractions (SerpAPI): {type(e).__name__}: {e}")
        return []


# ---------------------------------------------------------------------------
# DATA: Curated fallback attraction data by city
# ---------------------------------------------------------------------------
CITY_DATA = {
    "goa": [
        ("Baga Beach", "beach", 15.5524, 73.7522, 4.6, 20000, 3.0, 0.0, False, "morning", False,
         "One of Goa's most popular beaches, famous for water sports, shacks and nightlife"),
        ("Calangute Beach", "beach", 15.5437, 73.7546, 4.5, 18000, 3.0, 0.0, False, "morning", False,
         "The 'Queen of Beaches' — Goa's largest and most famous stretch of golden sand"),
        ("Basilica of Bom Jesus", "landmark", 15.5009, 73.9116, 4.8, 15000, 1.5, 0.0, True, "morning", False,
         "UNESCO World Heritage Site housing the mortal remains of St Francis Xavier"),
        ("Se Cathedral", "landmark", 15.5028, 73.9108, 4.7, 12000, 1.0, 0.0, True, "morning", False,
         "One of Asia's largest churches, a stunning example of Portuguese baroque architecture"),
        ("Dudhsagar Waterfalls", "park", 15.3144, 74.3144, 4.8, 14000, 4.0, 400.0, False, "morning", True,
         "Spectacular four-tiered waterfall on the Mandovi River — one of India's tallest"),
        ("Fort Aguada", "landmark", 15.4927, 73.7736, 4.6, 11000, 1.5, 0.0, False, "morning", False,
         "17th-century Portuguese fort with a famous lighthouse and panoramic sea views"),
        ("Anjuna Beach & Flea Market", "shopping", 15.5766, 73.7394, 4.5, 13000, 3.0, 0.0, False, "afternoon", False,
         "Iconic hippie beach famous for its Wednesday flea market, cafés and artistic vibe"),
        ("Palolem Beach", "beach", 15.0102, 74.0230, 4.7, 10000, 3.0, 0.0, False, "morning", False,
         "A crescent-shaped paradise in South Goa with calm waters and laid-back beach shacks"),
        ("Chapora Fort", "landmark", 15.5994, 73.7394, 4.5, 9000, 1.0, 0.0, False, "afternoon", False,
         "Atmospheric ruined fort with sweeping views over Vagator and the Arabian Sea"),
        ("Fontainhas Latin Quarter", "neighborhood", 15.4983, 73.8313, 4.7, 8000, 2.0, 0.0, False, "any", False,
         "Goa's charming Portuguese quarter with colourful houses, art galleries and cafés"),
        ("Spice Plantation Tour", "activity", 15.4020, 74.0140, 4.7, 7500, 3.0, 600.0, False, "morning", True,
         "Immersive tour of a lush spice farm with a traditional Goan lunch included"),
        ("Vagator Beach", "beach", 15.5986, 73.7441, 4.6, 9500, 2.5, 0.0, False, "afternoon", False,
         "Dramatic red-cliffed beach with a bohemian atmosphere and famous sunset parties"),
        ("Goa State Museum", "museum", 15.4916, 73.8210, 4.3, 5000, 1.5, 20.0, True, "any", False,
         "Fascinating museum tracing Goa's history from prehistoric times through Portuguese rule"),
        ("Dolphin Watching Cruise", "activity", 15.4909, 73.7730, 4.6, 8000, 2.0, 500.0, False, "morning", True,
         "Boat trip along the Goan coast to spot dolphins in their natural habitat"),
        ("Arambol Beach", "beach", 15.6863, 73.7049, 4.6, 7000, 3.0, 0.0, False, "any", False,
         "North Goa's most tranquil beach, beloved by artists and long-stay travellers"),
    ],
    "mumbai": [
        ("Gateway of India", "landmark", 18.9220, 72.8347, 4.6, 25000, 1.5, 0.0, False, "morning", False,
         "Iconic 1924 archway on the harbour front — Mumbai's most recognisable symbol"),
        ("Chhatrapati Shivaji Maharaj Terminus", "landmark", 18.9398, 72.8355, 4.7, 20000, 1.0, 0.0, False, "any", False,
         "UNESCO-listed Victorian Gothic railway station, one of the finest in the world"),
        ("Marine Drive", "neighborhood", 18.9438, 72.8230, 4.7, 22000, 2.0, 0.0, False, "evening", False,
         "Mumbai's famous 3-km seaside promenade, the 'Queen's Necklace' by night"),
        ("Elephanta Caves", "landmark", 18.9633, 72.9315, 4.5, 14000, 3.0, 40.0, False, "morning", True,
         "UNESCO World Heritage rock-cut cave temples dedicated to Lord Shiva on Elephanta Island"),
        ("Colaba Causeway", "shopping", 18.9068, 72.8322, 4.5, 16000, 2.5, 0.0, False, "afternoon", False,
         "Buzzing street market for antiques, handicrafts, clothes and street food"),
        ("Chhatrapati Shivaji Maharaj Museum", "museum", 18.9266, 72.8330, 4.7, 11000, 2.5, 85.0, True, "any", True,
         "Mumbai's premier art and history museum in a beautiful Indo-Saracenic building"),
        ("Juhu Beach", "beach", 19.0928, 72.8269, 4.3, 18000, 2.0, 0.0, False, "evening", False,
         "Famous Mumbai beach popular for evening walks and street food like pav bhaji and chaat"),
        ("Bandra-Worli Sea Link", "landmark", 19.0334, 72.8184, 4.7, 12000, 0.5, 0.0, False, "evening", False,
         "Stunning cable-stayed bridge across Mahim Bay — best seen illuminated at night"),
        ("Haji Ali Dargah", "landmark", 18.9827, 72.8094, 4.7, 14000, 1.0, 0.0, True, "morning", False,
         "Beautiful 15th-century mosque and tomb on a tiny islet, accessible at low tide"),
        ("Sanjay Gandhi National Park", "park", 19.2147, 72.9100, 4.6, 9000, 3.0, 48.0, False, "morning", False,
         "Vast forest park within Mumbai city with leopards, deer and ancient Kanheri Caves"),
        ("Sassoon Docks", "activity", 18.9133, 72.8345, 4.5, 7000, 1.5, 0.0, False, "morning", False,
         "Mumbai's oldest and most atmospheric fish market, best experienced at sunrise"),
        ("Banganga Tank", "landmark", 18.9564, 72.7978, 4.6, 6000, 1.0, 0.0, False, "morning", False,
         "Ancient sacred water tank surrounded by temples — a tranquil slice of old Mumbai"),
        ("Mahalaxmi Dhobi Ghat", "activity", 18.9622, 72.8343, 4.5, 10000, 1.0, 0.0, False, "morning", False,
         "The world's largest open-air laundry — a fascinating slice of Mumbai life"),
        ("Mohammed Ali Road Food Walk", "food", 18.9595, 72.8336, 4.8, 9500, 2.0, 0.0, False, "evening", False,
         "Mumbai's most celebrated street food strip, especially magical during Ramadan"),
        ("Dharavi Walk", "activity", 19.0436, 72.8540, 4.6, 8000, 3.0, 500.0, False, "morning", True,
         "Insightful guided tour of Asia's largest urban settlement, showcasing enterprise and resilience"),
    ],
    "paris": [
        ("Eiffel Tower", "landmark", 48.8584, 2.2945, 4.7, 25000, 2.0, 25.0, False, "morning", True,
         "Iconic iron lattice tower with panoramic views of Paris"),
        ("Louvre Museum", "museum", 48.8606, 2.3376, 4.8, 30000, 3.0, 18.0, True, "any", True,
         "World's largest art museum housing the Mona Lisa and thousands of masterpieces"),
        ("Notre-Dame Cathedral", "landmark", 48.8530, 2.3499, 4.6, 18000, 1.5, 0.0, False, "morning", False,
         "Medieval Gothic cathedral on the Île de la Cité, an architectural masterpiece"),
        ("Sacré-Cœur Basilica", "landmark", 48.8867, 2.3431, 4.7, 20000, 1.5, 0.0, False, "morning", False,
         "Stunning white basilica crowning Montmartre with sweeping city views"),
        ("Musée d'Orsay", "museum", 48.8600, 2.3266, 4.7, 15000, 2.5, 16.0, True, "afternoon", True,
         "Impressionist art museum in a stunning converted railway station"),
        ("Arc de Triomphe", "landmark", 48.8738, 2.2950, 4.6, 12000, 1.0, 13.0, False, "any", False,
         "Monumental arch at the head of the Champs-Élysées, honouring fallen soldiers"),
        ("Champs-Élysées", "shopping", 48.8698, 2.3077, 4.5, 10000, 2.0, 0.0, False, "afternoon", False,
         "World-famous boulevard lined with luxury shops, cafés, and theatres"),
        ("Luxembourg Gardens", "park", 48.8462, 2.3371, 4.6, 8000, 2.0, 0.0, False, "afternoon", False,
         "Beautiful 17th-century formal gardens perfect for a relaxing stroll"),
        ("Montmartre", "neighborhood", 48.8867, 2.3431, 4.7, 15000, 3.0, 0.0, False, "any", False,
         "Bohemian hilltop village famous for its art scene, windmills and charming streets"),
        ("Seine River Cruise", "activity", 48.8566, 2.3522, 4.5, 7000, 1.5, 20.0, False, "evening", True,
         "Scenic boat tour along the Seine passing Paris's most iconic monuments"),
        ("Le Marais District", "neighborhood", 48.8560, 2.3622, 4.6, 9000, 2.5, 0.0, False, "any", False,
         "Trendy historic district packed with galleries, boutiques, and Jewish heritage"),
        ("Sainte-Chapelle", "landmark", 48.8554, 2.3451, 4.8, 11000, 1.0, 11.0, True, "morning", True,
         "Exquisite Gothic chapel renowned for 15 floor-to-ceiling stained-glass windows"),
        ("Palace of Versailles", "landmark", 48.8049, 2.1204, 4.8, 22000, 4.0, 20.0, False, "morning", True,
         "Opulent royal palace and gardens that defined European court culture"),
        ("Latin Quarter", "neighborhood", 48.8521, 2.3434, 4.5, 7500, 2.5, 0.0, False, "any", False,
         "Lively student district with narrow medieval streets, bookshops and lively cafés"),
        ("Tuileries Garden", "park", 48.8634, 2.3275, 4.5, 6000, 1.5, 0.0, False, "afternoon", False,
         "Elegant public garden stretching between the Louvre and Place de la Concorde"),
    ],
    "london": [
        ("Tower of London", "landmark", 51.5081, -0.0759, 4.7, 20000, 2.5, 29.0, False, "morning", True,
         "Historic castle on the Thames housing the Crown Jewels and a 1000-year history"),
        ("British Museum", "museum", 51.5194, -0.1270, 4.8, 28000, 3.0, 0.0, True, "any", False,
         "World-class museum with over 8 million artefacts including the Rosetta Stone"),
        ("Buckingham Palace", "landmark", 51.5014, -0.1419, 4.6, 18000, 1.5, 0.0, False, "morning", False,
         "Official London residence of the monarch; catch the Changing of the Guard"),
        ("Tower Bridge", "landmark", 51.5055, -0.0754, 4.7, 15000, 1.0, 11.0, False, "any", False,
         "Victorian Gothic bascule bridge offering stunning views of the Thames"),
        ("National Gallery", "museum", 51.5094, -0.1283, 4.7, 14000, 2.5, 0.0, True, "afternoon", False,
         "Iconic art museum on Trafalgar Square with over 2300 Western European paintings"),
        ("Hyde Park", "park", 51.5073, -0.1657, 4.6, 12000, 2.0, 0.0, False, "afternoon", False,
         "Royal park in the heart of London ideal for cycling, rowing and relaxing"),
        ("Covent Garden", "shopping", 51.5117, -0.1240, 4.5, 10000, 2.0, 0.0, False, "afternoon", False,
         "Vibrant piazza filled with boutique shops, street performers and great food"),
        ("Westminster Abbey", "landmark", 51.4994, -0.1273, 4.8, 16000, 1.5, 27.0, True, "morning", True,
         "Gothic abbey church where British monarchs are crowned and many are buried"),
        ("The Shard", "landmark", 51.5045, -0.0865, 4.5, 8000, 1.5, 32.0, True, "evening", True,
         "Western Europe's tallest skyscraper with a spectacular observation deck"),
        ("Borough Market", "food", 51.5055, -0.0910, 4.7, 9000, 1.5, 0.0, False, "morning", False,
         "London's oldest and most celebrated food market with artisan producers"),
        ("Tate Modern", "museum", 51.5076, -0.0994, 4.6, 13000, 2.5, 0.0, True, "any", False,
         "World-leading modern art museum in a converted Bankside power station"),
        ("Greenwich Park", "park", 51.4769, 0.0005, 4.7, 7000, 2.0, 0.0, False, "afternoon", False,
         "Royal park with panoramic London views and the Prime Meridian Line"),
        ("Portobello Road Market", "shopping", 51.5152, -0.2042, 4.5, 7500, 2.0, 0.0, False, "any", False,
         "Famous antiques and street food market in lovely Notting Hill"),
        ("St Paul's Cathedral", "landmark", 51.5138, -0.0984, 4.7, 11000, 1.5, 20.0, True, "morning", False,
         "Christopher Wren's baroque masterpiece with its famous Whispering Gallery"),
        ("Kew Gardens", "park", 51.4787, -0.2956, 4.8, 9500, 3.0, 22.0, False, "afternoon", True,
         "UNESCO World Heritage Site with the world's most diverse plant collection"),
    ],
    "new york": [
        ("Statue of Liberty", "landmark", 40.6892, -74.0445, 4.7, 30000, 3.0, 24.0, False, "morning", True,
         "Iconic neoclassical sculpture on Liberty Island — symbol of freedom and democracy"),
        ("Central Park", "park", 40.7851, -73.9683, 4.8, 35000, 2.5, 0.0, False, "any", False,
         "Vast urban oasis at the heart of Manhattan perfect for walks, cycling and picnics"),
        ("Metropolitan Museum of Art", "museum", 40.7794, -73.9632, 4.8, 28000, 3.0, 30.0, True, "any", False,
         "One of the world's greatest art museums with over 5000 years of history"),
        ("Empire State Building", "landmark", 40.7484, -73.9967, 4.7, 25000, 1.5, 44.0, True, "evening", True,
         "Art Deco skyscraper with a breathtaking observation deck on the 86th floor"),
        ("Times Square", "neighborhood", 40.7580, -73.9855, 4.5, 20000, 1.5, 0.0, False, "evening", False,
         "Dazzling commercial hub known as 'The Crossroads of the World'"),
        ("Brooklyn Bridge", "landmark", 40.7061, -73.9969, 4.7, 18000, 1.0, 0.0, False, "morning", False,
         "Iconic 1883 bridge offering spectacular views of the Manhattan skyline"),
        ("High Line", "park", 40.7480, -74.0048, 4.6, 14000, 2.0, 0.0, False, "afternoon", False,
         "Elevated linear park on a former rail line with public art and great city views"),
        ("MoMA", "museum", 40.7614, -73.9776, 4.7, 16000, 2.5, 30.0, True, "any", True,
         "World-renowned modern and contemporary art museum featuring Van Gogh and Picasso"),
        ("One World Observatory", "landmark", 40.7127, -74.0134, 4.7, 12000, 1.5, 40.0, True, "evening", True,
         "Observation deck atop One World Trade Center with 360° views of New York"),
        ("DUMBO Brooklyn", "neighborhood", 40.7033, -73.9881, 4.6, 9000, 2.0, 0.0, False, "afternoon", False,
         "Hip Brooklyn neighbourhood with cobblestones, art galleries and stunning bridge views"),
        ("Rockefeller Center", "landmark", 40.7587, -73.9787, 4.6, 11000, 1.5, 38.0, False, "any", False,
         "Art Deco complex with Top of the Rock observation deck and iconic ice rink"),
        ("Natural History Museum", "museum", 40.7813, -73.9740, 4.7, 17000, 2.5, 28.0, True, "any", False,
         "Fascinating museum housing the world-famous blue whale, dinosaurs and planetarium"),
        ("Chelsea Market", "food", 40.7424, -74.0062, 4.6, 8000, 1.5, 0.0, True, "any", False,
         "Bustling indoor food hall in a historic factory building with artisan vendors"),
        ("The Frick Collection", "museum", 40.7709, -73.9669, 4.8, 7000, 1.5, 22.0, True, "afternoon", False,
         "Intimate mansion museum with masterworks by Vermeer, Rembrandt and Turner"),
        ("Coney Island Beach", "park", 40.5749, -73.9857, 4.4, 8500, 3.0, 0.0, False, "afternoon", False,
         "Legendary seaside amusement area with iconic boardwalk, rides and beach"),
    ],
    "tokyo": [
        ("Senso-ji Temple", "landmark", 35.7148, 139.7967, 4.8, 22000, 2.0, 0.0, False, "morning", False,
         "Tokyo's oldest and most famous Buddhist temple in the historic Asakusa district"),
        ("Shibuya Crossing", "neighborhood", 35.6595, 139.7004, 4.7, 25000, 1.0, 0.0, False, "evening", False,
         "World's busiest pedestrian crossing — an electrifying symbol of modern Tokyo"),
        ("Tokyo National Museum", "museum", 35.7188, 139.7762, 4.7, 18000, 2.5, 10.0, True, "any", False,
         "Japan's oldest and largest museum with over 110,000 objects of Japanese art"),
        ("Shinjuku Gyoen", "park", 35.6852, 139.7100, 4.7, 15000, 2.5, 5.0, False, "afternoon", False,
         "Beautiful national garden blending French formal, English landscape and Japanese styles"),
        ("teamLab Borderless", "activity", 35.6245, 139.7758, 4.9, 20000, 2.5, 32.0, True, "any", True,
         "Immersive digital art museum where artworks move freely between rooms"),
        ("Meiji Shrine", "landmark", 35.6763, 139.6993, 4.6, 16000, 1.5, 0.0, False, "morning", False,
         "Forested Shinto shrine dedicated to Emperor Meiji — a serene oasis in Harajuku"),
        ("Tsukiji Outer Market", "food", 35.6655, 139.7707, 4.6, 12000, 1.5, 0.0, False, "morning", False,
         "Vibrant market with fresh seafood, street food and chef-grade produce"),
        ("Harajuku Takeshita Street", "shopping", 35.6702, 139.7027, 4.5, 10000, 2.0, 0.0, False, "afternoon", False,
         "Colourful pedestrian street famous for quirky street fashion and crepe shops"),
        ("Tokyo Skytree", "landmark", 35.7101, 139.8107, 4.7, 14000, 1.5, 21.0, True, "evening", True,
         "World's tallest broadcast tower at 634m with two observation decks"),
        ("Akihabara Electric Town", "shopping", 35.7023, 139.7745, 4.6, 11000, 2.5, 0.0, False, "afternoon", False,
         "Tokyo's famous electronics and anime hub packed with gadget shops and arcades"),
        ("Ueno Park", "park", 35.7156, 139.7732, 4.5, 9000, 2.0, 0.0, False, "afternoon", False,
         "Large park housing several major museums, Ueno Zoo and beautiful cherry trees"),
        ("Yanaka Old Town", "neighborhood", 35.7270, 139.7695, 4.7, 7000, 2.5, 0.0, False, "any", False,
         "Charming preserved old neighbourhood with temples, studios and craftspeople"),
        ("Odaiba Island", "activity", 35.6270, 139.7750, 4.5, 8500, 3.0, 0.0, False, "afternoon", False,
         "Futuristic artificial island with shopping, museums and a Gundam statue"),
        ("Shinjuku Golden Gai", "neighborhood", 35.6938, 139.7038, 4.6, 8000, 2.0, 0.0, False, "evening", False,
         "Labyrinth of tiny atmospheric bars beloved by locals and creatives alike"),
        ("Imperial Palace East Garden", "park", 35.6863, 139.7539, 4.7, 9500, 1.5, 0.0, False, "morning", False,
         "Beautifully kept gardens on the former site of Edo Castle's innermost citadel"),
    ],
    "rome": [
        ("Colosseum", "landmark", 41.8902, 12.4922, 4.8, 28000, 2.5, 16.0, False, "morning", True,
         "Ancient amphitheatre that once held 80,000 spectators for gladiatorial contests"),
        ("Vatican Museums & Sistine Chapel", "museum", 41.9065, 12.4536, 4.8, 25000, 3.5, 21.0, True, "any", True,
         "Extraordinary museums culminating in Michelangelo's breathtaking Sistine Chapel"),
        ("Roman Forum", "landmark", 41.8925, 12.4853, 4.6, 18000, 2.0, 12.0, False, "morning", False,
         "The ancient centre of Roman public life surrounded by ruins of temples and arches"),
        ("Trevi Fountain", "landmark", 41.9009, 12.4833, 4.7, 22000, 0.5, 0.0, False, "evening", False,
         "Spectacular Baroque fountain — toss a coin to ensure your return to Rome"),
        ("Pantheon", "landmark", 41.8986, 12.4769, 4.8, 20000, 1.0, 0.0, False, "morning", False,
         "Best-preserved ancient Roman building with a remarkable unreinforced concrete dome"),
        ("Borghese Gallery", "museum", 41.9138, 12.4922, 4.8, 12000, 2.0, 15.0, True, "afternoon", True,
         "Intimate gallery with Bernini sculptures and Caravaggio masterpieces in a villa"),
        ("Piazza Navona", "neighborhood", 41.8992, 12.4731, 4.6, 14000, 1.0, 0.0, False, "any", False,
         "Lively Baroque square with three fountains, street artists and outdoor cafés"),
        ("Trastevere", "neighborhood", 41.8896, 12.4697, 4.7, 11000, 2.5, 0.0, False, "evening", False,
         "Rome's most charming neighbourhood with ivy-clad alleys, trattorias and piazzas"),
        ("Palatine Hill", "landmark", 41.8893, 12.4875, 4.6, 9000, 2.0, 12.0, False, "morning", False,
         "The legendary founding hill of Rome with stunning views over the Circus Maximus"),
        ("Campo de' Fiori", "food", 41.8956, 12.4722, 4.5, 8000, 1.0, 0.0, False, "morning", False,
         "Vibrant daily market square that transforms into a popular evening gathering place"),
        ("Castel Sant'Angelo", "landmark", 41.9031, 12.4663, 4.7, 13000, 1.5, 15.0, True, "afternoon", False,
         "Imposing fortress on the Tiber originally built as a mausoleum for Emperor Hadrian"),
        ("Appian Way", "park", 41.8538, 12.5201, 4.6, 7000, 3.0, 0.0, False, "afternoon", False,
         "Ancient Roman road flanked by catacombs and countryside perfect for cycling"),
        ("Maxxi Museum", "museum", 41.9293, 12.4661, 4.5, 6000, 2.0, 12.0, True, "afternoon", False,
         "Zaha Hadid's striking contemporary art and architecture museum"),
        ("Circus Maximus", "landmark", 41.8860, 12.4844, 4.4, 7500, 0.5, 0.0, False, "any", False,
         "Ancient chariot racing stadium capable of holding a quarter million spectators"),
        ("Aventine Keyhole", "landmark", 41.8832, 12.4785, 4.8, 6500, 0.5, 0.0, False, "morning", False,
         "A tiny keyhole offering a perfectly framed view of St Peter's Dome — a hidden gem"),
    ],
}


def generate_fallback_attractions(request, constraints) -> List[Attraction]:
    """
    Return curated fallback attractions for the destination when the live API is unavailable.
    Falls back to generic entries for unknown cities.
    """
    destination = request.destination.split(",")[0].strip() if request.destination else "Paris"
    city_key = destination.lower()

    city_attractions = CITY_DATA.get(city_key)

    if city_attractions is None:
        generic_names = [
            (f"City Museum of {destination}", "museum", 0, 0, 4.5, 10000, 2.5, 12.0, True, "any", False,
             f"The main cultural museum showcasing the history and heritage of {destination}"),
            (f"{destination} Old Town", "neighborhood", 0, 0, 4.6, 12000, 2.5, 0.0, False, "any", False,
             f"Historic old town centre with charming streets, local cafés and landmarks"),
            (f"{destination} Central Park", "park", 0, 0, 4.4, 8000, 2.0, 0.0, False, "afternoon", False,
             f"The main public park of {destination}, popular with locals and visitors alike"),
            (f"{destination} Art Gallery", "museum", 0, 0, 4.5, 7000, 2.0, 8.0, True, "any", False,
             f"Regional art gallery with a strong collection of local and national artworks"),
            (f"Cathedral of {destination}", "landmark", 0, 0, 4.6, 9000, 1.5, 0.0, False, "morning", False,
             f"The grand historic cathedral at the spiritual heart of {destination}"),
            (f"{destination} Waterfront", "neighborhood", 0, 0, 4.5, 8500, 2.0, 0.0, False, "afternoon", False,
             f"Scenic waterfront promenade perfect for an evening stroll"),
            (f"{destination} Food Market", "food", 0, 0, 4.6, 7500, 1.5, 0.0, False, "morning", False,
             f"Bustling local market with fresh produce, street food and artisan goods"),
            (f"{destination} Botanical Garden", "park", 0, 0, 4.5, 6000, 2.0, 5.0, False, "afternoon", False,
             f"Beautiful botanical garden with exotic plants and peaceful walking paths"),
            (f"Historic Fortress of {destination}", "landmark", 0, 0, 4.6, 9500, 2.0, 10.0, False, "morning", False,
             f"Ancient fortress offering panoramic views and centuries of military history"),
            (f"{destination} Panoramic Viewpoint", "landmark", 0, 0, 4.7, 8000, 1.0, 0.0, False, "evening", False,
             f"The highest point in {destination} with sweeping views of the city and surroundings"),
            (f"Contemporary Art Centre {destination}", "museum", 0, 0, 4.4, 5000, 1.5, 8.0, True, "afternoon", False,
             f"Modern art centre showcasing cutting-edge local and international artists"),
            (f"{destination} Night Market", "food", 0, 0, 4.5, 7000, 2.0, 0.0, False, "evening", False,
             f"Lively night market with street food, crafts and local entertainment"),
            (f"Archaeological Site of {destination}", "landmark", 0, 0, 4.5, 8000, 2.0, 7.0, False, "morning", False,
             f"Fascinating archaeological site revealing the ancient origins of {destination}"),
            (f"{destination} Shopping District", "shopping", 0, 0, 4.3, 9000, 2.5, 0.0, False, "afternoon", False,
             f"Main shopping area with a mix of local boutiques and international brands"),
            (f"Riverside Walk, {destination}", "park", 0, 0, 4.6, 6500, 2.0, 0.0, False, "any", False,
             f"Scenic riverside walk with benches, street performers and lovely views"),
        ]
        city_attractions = generic_names

    attractions = []
    for i, row in enumerate(city_attractions):
        name, category, lat, lon, rating, reviews, duration, cost, indoor, best_time, booking, description = row
        attraction = Attraction(
            id=f"attraction_{i + 1}",
            name=name,
            category=category,
            location=GeoLocation(
                latitude=lat,
                longitude=lon,
                address=f"{name}, {destination}",
                city=destination,
                country="",
            ),
            rating=rating,
            num_reviews=reviews,
            estimated_duration_hours=duration,
            cost=cost,
            indoor=indoor,
            best_time=best_time,
            requires_booking=booking,
            description=description,
            opening_hours="9:00 AM – 6:00 PM" if category == "museum" else "Open daily",
        )
        attractions.append(attraction)

    return attractions


def score_attractions(attractions: List[Attraction], constraints) -> List[Attraction]:
    """Score attractions by rating, popularity, cost and preference alignment."""
    for attraction in attractions:
        rating_score = (attraction.rating / 5.0) * 100
        popularity_score = min(100, (attraction.num_reviews / 1000) * 10)

        if attraction.cost == 0:
            cost_score = 100
        elif attraction.cost < 15:
            cost_score = 80
        else:
            cost_score = max(50, 100 - (attraction.cost * 2))

        attraction.score = (
            rating_score * 0.5 + popularity_score * 0.3 + cost_score * 0.2
        )

        activity_prefs = []
        if constraints:
            if hasattr(constraints, "soft") and constraints.soft:
                activity_prefs = constraints.soft.interests or []

        if activity_prefs:
            for pref in activity_prefs:
                if pref.lower() in attraction.category.lower() or pref.lower() in attraction.name.lower():
                    attraction.score += 10
                    break

    return sorted(attractions, key=lambda x: x.score, reverse=True)


def categorize_attractions(attractions: List[Attraction]) -> AttractionList:
    """Group attractions into top_rated, budget_friendly, outdoor and indoor buckets."""
    top_rated = [a for a in attractions if a.score >= 85][:10]

    budget_friendly = sorted(
        [a for a in attractions if a.cost < 10],
        key=lambda x: x.score,
        reverse=True,
    )[:10]

    outdoor = sorted(
        [a for a in attractions if not a.indoor],
        key=lambda x: x.score,
        reverse=True,
    )[:10]

    indoor = sorted(
        [a for a in attractions if a.indoor],
        key=lambda x: x.score,
        reverse=True,
    )[:10]

    return AttractionList(
        all_attractions=attractions,
        top_rated=top_rated,
        budget_friendly=budget_friendly,
        outdoor_activities=outdoor,
        indoor_activities=indoor,
    )
