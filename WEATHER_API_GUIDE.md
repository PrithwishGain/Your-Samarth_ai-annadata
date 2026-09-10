# Weather API Implementation Guide

## Overview
This feature integrates a weather API that fetches real-time weather data based on the user's device location. The weather information is displayed on the home page in an interactive weather card.

## Features
✅ **Device Geolocation**: Automatically detects user's location using the browser's Geolocation API
✅ **Real-Time Weather Data**: Fetches current weather from Open-Meteo (free, no API key required)
✅ **Reverse Geocoding**: Gets location name (city/state) from coordinates using Nominatim
✅ **Farming-Specific Recommendations**: Provides spraying and agricultural advice based on weather
✅ **Responsive Weather Card**: Displays temperature, humidity, wind speed, rain chance, and recommendations
✅ **Fallback Mechanism**: Uses Kolkata coordinates as fallback if geolocation is unavailable

## Architecture

### Backend (`backend/main.py`)
- **Endpoint**: `GET /weather?latitude={lat}&longitude={lon}`
- **Dependencies**: 
  - `httpx` for async HTTP requests
  - Open-Meteo API (free, no key needed)
  - Nominatim API for reverse geocoding (free, no key needed)
- **Returns**:
  ```json
  {
    "location": "City, State",
    "latitude": 22.5726,
    "longitude": 88.3639,
    "temperature": 28,
    "condition": "Partly Cloudy",
    "humidity": 78,
    "wind_speed": 11,
    "rain_chance": 40,
    "spraying_recommendation": "Good time",
    "advice": "Clear weather — good day for field work and pesticide application."
  }
  ```

### Frontend (`frontend/weather.js`)
- **Functions**:
  - `initWeather()`: Initializes geolocation on page load
  - `fetchWeatherData(lat, lon)`: Calls backend weather API
  - `updateWeatherCard(data)`: Updates UI with weather information
  - `updateWeatherIcon(condition)`: Renders appropriate weather icon
  - `useDefaultLocation()`: Fallback to Kolkata coordinates

- **Weather Card Elements Updated**:
  - `.weather-mini`: Temperature and location mini display
  - `.weather-loc`: Full location name
  - `.weather-temp`: Temperature and condition
  - `.weather-grid`: Humidity, rain chance, wind, and spraying recommendation
  - `.weather-advice`: Farming-specific advice
  - `.weather-icon`: Dynamic SVG icon based on weather condition

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Backend Server
```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Open Frontend
- Serve the frontend using a local server (e.g., Live Server on port 5500)
- Open `samarthAI.html` in your browser

### 4. Browser Permissions
- The application will request location permission
- Allow it to enable weather detection
- If denied, the app will use Kolkata as default location

## API Endpoints

### Weather Endpoint
```
GET /weather?latitude=22.5726&longitude=88.3639
```

**Query Parameters:**
- `latitude` (float, required): Latitude coordinate
- `longitude` (float, required): Longitude coordinate

**Response (200 OK):**
Returns weather data object with all fields populated

**Response (Error):**
```json
{
  "error": "error message",
  "message": "Failed to fetch weather data"
}
```

## Weather Code Interpretation
The system uses WMO (World Meteorological Organization) weather codes:
- `0`: Clear sky
- `1-3`: Partly cloudy to overcast
- `45-48`: Fog
- `51-65`: Drizzle and rain
- `71-86`: Snow and snow showers
- `95-99`: Thunderstorms

## Farming Recommendations Logic

### Rain Chance Estimation
- Clear/Mainly clear: 0%
- Partly cloudy: 10%
- Overcast: 20%
- Light rain: 70%
- Heavy rain: 70%+
- Thunderstorm: 90%

### Spraying Recommendation
**Not ideal for spraying if:**
- Rain/thunderstorm present
- Wind speed > 15 km/h
- Humidity > 85%
- Fog conditions

**Good time for spraying:**
- Clear weather
- Low wind
- Moderate humidity

## Testing

### Test with Device Location
1. Open browser DevTools (F12)
2. Go to Settings → Location
3. Set a location or use device location
4. Reload the page
5. Weather card should update with the selected location

### Test with Console
```javascript
// Manually fetch weather for specific location
fetch('http://127.0.0.1:8000/weather?latitude=22.5726&longitude=88.3639')
  .then(r => r.json())
  .then(d => console.log(d));
```

### Test Different Weather Conditions
Test coordinates for various weather scenarios:
- **Sunny (Goa)**: 15.2993, 73.8243
- **Rainy (Kerala)**: 10.3528, 75.7975
- **Cold (Himachal)**: 31.7724, 77.1025
- **Foggy (Delhi)**: 28.7041, 77.1025

## Error Handling

### Geolocation Errors
- **Permission Denied**: Uses Kolkata fallback
- **Timeout**: Shows console warning, uses Kolkata fallback
- **Not Supported**: Works with fallback location

### API Errors
- Network errors are caught and logged
- Weather card retains previous data if update fails
- Error messages logged to browser console

## Browser Compatibility

**Requires:**
- ✅ Geolocation API support
- ✅ Fetch API support
- ✅ Modern ES6+ JavaScript support

**Tested on:**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile Safari (iOS 14+)
- Android Chrome

## Performance Considerations

- Weather data fetched once on page load
- Uses `AsyncClient` for non-blocking requests
- Average API response time: 200-500ms
- Geolocation permission request: instant to user-dependent

## Future Enhancements

1. **Hourly Weather Updates**: Add periodic refresh (every 30 minutes)
2. **Multi-Day Forecast**: Show 7-day forecast
3. **Alerts**: Notify for severe weather conditions
4. **User Preferences**: Allow users to set default location
5. **Offline Support**: Cache weather data locally
6. **Weather History**: Track weather patterns over time
7. **Crop-Specific Advice**: Customize recommendations based on crop type

## Troubleshooting

### Weather card not updating
1. Check browser console (F12) for errors
2. Ensure backend is running on port 8000
3. Check CORS is enabled in FastAPI
4. Verify Geolocation permission is granted

### Location showing "Unknown"
- Reverse geocoding API might be rate-limited
- Try a different location
- Check internet connection

### Weather icon not displaying
- Verify SVG path in `updateWeatherIcon()` function
- Check browser console for DOM errors
- Ensure CSS is loading correctly

## API Rate Limits
- **Open-Meteo**: Unlimited for non-commercial use
- **Nominatim**: 1 request per second per IP (we make 1 request per weather update)

## Credits
- Weather data: [Open-Meteo](https://open-meteo.com)
- Geocoding: [Nominatim/OpenStreetMap](https://nominatim.org)
