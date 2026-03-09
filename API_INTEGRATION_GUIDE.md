# API Integration Guide for Real-Time Data
# ==========================================

## Overview
This document explains how to set up real-time API integrations for the travel planner.

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your API keys to `.env`:**
   - OpenAI or Anthropic (required)
   - Amadeus (flights)
   - OpenWeatherMap (weather)
   - Google Places (attractions)

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the planner:**
   ```bash
   python -m src.main
   ```

## API Setup Instructions

### 1. Amadeus (Flight Search) ✈️

**Free Tier:** 2,000 API calls/month

1. Sign up: https://developers.amadeus.com/register
2. Create a new app in the dashboard
3. Get your API Key and Secret
4. Add to `.env`:
   ```
   AMADEUS_API_KEY=your_api_key
   AMADEUS_API_SECRET=your_api_secret
   ```

**Features:**
- Real-time flight search
- Multiple airlines
- Price comparison
- Direct and connecting flights

---

### 2. OpenWeatherMap (Weather Data) ☁️

**Free Tier:** 1,000 API calls/day

1. Sign up: https://home.openweathermap.org/users/sign_up
2. Get your API key from account settings
3. Add to `.env`:
   ```
   OPENWEATHER_API_KEY=your_api_key
   ```

**Features:**
- 5-day weather forecast
- Hourly updates
- Temperature, precipitation, wind
- Sunrise/sunset times

---

### 3. Google Places API (Attractions) 🗺️

**Free Tier:** $200 credit/month (~28,500 Place Details requests)

1. Go to: https://console.cloud.google.com/
2. Create a new project
3. Enable APIs:
   - Places API
   - Geocoding API
4. Create credentials (API Key)
5. Add to `.env`:
   ```
   GOOGLE_PLACES_API_KEY=your_api_key
   ```

**Features:**
- Tourist attractions
- Museums, landmarks, parks
- Ratings and reviews
- Opening hours
- Photos

---

### 4. Hotel Search (Optional) 🏨

**Note:** Hotel APIs require special partner/affiliate approval:

#### Option A: Booking.com Partner API
- Apply: https://partners.booking.com/
- Requires business verification
- Best for production use

#### Option B: RapidAPI Hotels
- Sign up: https://rapidapi.com/
- Search for hotel APIs (Hotels.com, Booking.com proxies)
- Free tiers available
- Easier to get started

#### Option C: Expedia Partner Solutions
- Apply: https://expediapartnersolutions.com/
- Comprehensive hotel data
- Requires affiliate approval

**Current Behavior:**
- System uses curated hotel data
- Prices based on market averages
- Add a warning message to users

---

## API Fallback Strategy

The system is designed with graceful fallbacks:

1. **Try real-time API first**
2. **If API fails or unavailable:**
   - Use fallback estimates
   - Add warning message to results
   - Log the issue
   - Continue workflow

This ensures the system always works, even without API keys.

---

## Cost Estimates

### Free Tier Limits (per month):

| API | Free Calls | Typical Usage | Cost if Exceeded |
|-----|------------|---------------|------------------|
| Amadeus | 2,000 | ~200 trips | ~$0.50 per 1,000 |
| OpenWeatherMap | 30,000 | ~1,000 trips | $0.0012 per call |
| Google Places | $200 credit | ~280 trips | $0.017 per request |

**Total:** Free for ~200 trips/month

---

## Testing APIs

Test each API individually:

```bash
# Test Amadeus flights
python -c "
import asyncio
from src.utils.api_clients import amadeus_client
result = asyncio.run(amadeus_client.search_flights('JFK', 'CDG', '2026-06-01'))
print(f'Found {len(result)} flights')
"

# Test OpenWeather
python -c "
import asyncio
from src.utils.api_clients import weather_client
result = asyncio.run(weather_client.get_forecast('Paris'))
print(f'Weather data:', result is not None)
"

# Test Google Places
python -c "
import asyncio
from src.utils.api_clients import places_client
result = asyncio.run(places_client.search_nearby('48.8566,2.3522'))
print(f'Found {len(result)} places')
"
```

---

## Caching Strategy

Redis is used to cache API responses:

- **Flights:** 6 hours
- **Hotels:** 12 hours
- **Weather:** 3 hours
- **Places:** 7 days

**Setup Redis:**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

---

## Rate Limiting

The system implements rate limiting to avoid API quotas:

- Max 5 requests per minute per API
- Automatic retry with exponential backoff
- Queue requests if limit reached

---

## Production Checklist

- [ ] All API keys added to `.env`
- [ ] Redis installed and running
- [ ] Test each API endpoint
- [ ] Monitor API usage in dashboards
- [ ] Set up error alerting (Sentry)
- [ ] Configure caching TTLs
- [ ] Review rate limits
- [ ] Test fallback behavior
- [ ] Add usage analytics

---

## Troubleshooting

### "API credentials not configured"
- Check `.env` file exists
- Verify API key format
- Ensure no extra spaces

### "API rate limit exceeded"
- Wait for rate limit reset
- Check usage in API dashboard
- Consider upgrading plan

### "No results returned"
- Verify city names/codes
- Check date formats
- Review API documentation
- Test with curl/Postman first

---

## Support

For API-specific issues:
- **Amadeus:** https://developers.amadeus.com/support
- **OpenWeather:** https://openweathermap.org/faq
- **Google:** https://developers.google.com/maps/support

For system issues:
- Check logs in `logs/` directory
- Review error messages
- Search existing issues
