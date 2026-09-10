# Weather API Troubleshooting Guide

## ✅ What's Working

Backend is **100% working**! Verified with test script:
```
✓ Health endpoint returns: "Samarth AI backend is running"
✓ Weather endpoint returns real data:
  - Location: Kolkata, West Bengal
  - Temperature: 31°C
  - Condition: Light drizzle
  - Humidity: 78%
  - Wind: 6 km/h
  - Rain chance: 40%
  - Spraying: Good time
```

## 🔍 How to Debug Frontend

### Step 1: Open Browser Developer Console
1. Open `samarthAI.html` in your browser
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Look for messages starting with "✓" and "✗"

### Step 2: Expected Console Output
You should see logs like:
```
Weather.js loaded!
Checking document readyState: interactive
Document still loading, adding DOMContentLoaded listener
Starting weather initialization...
Initializing weather after DOM ready
initWeather() called
✓ Device location: 22.5726, 88.3639
(or: ✗ Geolocation error: User denied geolocation)
Fetching weather from: http://127.0.0.1:8000/weather?latitude=22.5726...
Response status: 200
Weather data received: {...}
Updating weather card with data: {...}
✓ Updated weather-mini: 31°C · Kolkata
✓ Updated weather-loc: Kolkata, West Bengal
✓ Updated weather-temp: 31°C Light drizzle
✓ Updated weather grid
✓ Updated weather-advice: ...
✓ Weather card update complete!
```

### Step 3: If You See Errors

**Error: "CORS error" or "Failed to fetch"**
- Make sure backend is running on http://127.0.0.1:8000
- Run: `python -m uvicorn main:app --host 127.0.0.1 --port 8000`

**Error: "weather-mini element not found"**
- Check that samarthAI.html has the weather card HTML
- Weather elements must exist in DOM before weather.js runs

**Error: "Expected 4+ weather grid elements, found X"**
- Check samarthAI.html for `.weather-grid div` elements
- Should have at least 4 div children

### Step 4: Manual Testing

**Option A: Use weather-test.html**
1. Open `frontend/weather-test.html` in browser
2. Click buttons to test each component:
   - "Test Health Endpoint" → Should show status OK
   - "Test Weather Endpoint" → Should show real weather data
   - "Get Device Location" → Should show your coordinates
   - "Run Full Test" → End-to-end test

**Option B: Use Python test script**
```bash
cd backend
python test_weather_api.py
```
Expected output:
```
Testing /health endpoint...
Health status: 200
Health response: {'status': 'ok', 'message': '...'}

Testing /weather endpoint...
Weather status: 200
Weather response:
{
  "location": "Kolkata, West Bengal",
  "temperature": 31,
  ...
}
```

## 🚀 Setup Checklist

- [ ] Backend installed dependencies: `pip install -r backend/requirements.txt`
- [ ] Backend server running: `python -m uvicorn main:app --host 127.0.0.1 --port 8000`
- [ ] Frontend HTML file: `frontend/samarthAI.html`
- [ ] Weather script loaded: `frontend/weather.js`
- [ ] Frontend served on http://localhost:5500 (or similar)
- [ ] Browser console showing "Weather.js loaded!"

## 📋 Common Issues & Solutions

### Issue 1: Nothing happens when page loads
**Solution:**
1. Open browser console (F12)
2. Look for "Weather.js loaded!" message
3. If missing: weather.js isn't loading
   - Check browser Network tab for 404 error
   - Verify script src="weather.js" in HTML
   - Check file exists: `frontend/weather.js`

### Issue 2: Backend connection fails
**Solution:**
1. Test health endpoint: Open `http://127.0.0.1:8000/health` in browser
2. If 404: Backend not running
3. If connection refused: Backend not started
4. Start backend: `cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000`

### Issue 3: Weather card doesn't update
**Solution:**
1. Check console for "✓ Weather card update complete!" message
2. If not there: Data didn't arrive from backend
3. Look for error messages in console
4. Click "Run Full Test" in weather-test.html for diagnosis

### Issue 4: Location permission denied
**Solution:**
- Browser will ask for permission to access location
- Click "Allow" to share location
- If you click "Block", app falls back to Kolkata
- To reset: Go to browser settings → Privacy → Clear location permission

## 🔧 Backend Server Commands

**Start server (will auto-reload on code changes):**
```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Start server (production mode):**
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**Test backend without frontend:**
```bash
cd backend
python test_weather_api.py
```

## 📊 File Structure

```
backend/
├── main.py                 ← FastAPI server
├── requirements.txt        ← Dependencies
└── test_weather_api.py    ← Test script

frontend/
├── samarthAI.html         ← Main page
├── weather.js             ← Weather module
├── weather-test.html      ← Debug page
├── app.js                 ← Other logic
└── styles.css             ← Styling
```

## 🌐 API Documentation

### Endpoint: GET /weather

**URL:**
```
http://127.0.0.1:8000/weather?latitude=22.5726&longitude=88.3639
```

**Query Parameters:**
- `latitude` (float) - Latitude coordinate
- `longitude` (float) - Longitude coordinate

**Success Response (200 OK):**
```json
{
  "location": "Kolkata, West Bengal",
  "latitude": 22.5726,
  "longitude": 88.3639,
  "temperature": 31,
  "condition": "Light drizzle",
  "humidity": 78,
  "wind_speed": 6,
  "rain_chance": 40,
  "spraying_recommendation": "Good time",
  "advice": "Monitor weather and plan accordingly."
}
```

**Error Response:**
```json
{
  "error": "error message",
  "message": "Failed to fetch weather data"
}
```

## 📱 Testing Locations

Test with different coordinates:
- Mumbai: 19.0760, 72.8777
- Bangalore: 12.9716, 77.5946
- Kerala: 10.3528, 75.7975
- Himachal: 31.7724, 77.1025

## 🎯 Next Steps

### If Everything Works:
- Weather displays on page load ✓
- Updates when location changes ✓
- Shows accurate data ✓
- Ready for production!

### If Still Issues:
1. Paste console output here for analysis
2. Check Network tab in DevTools for failed requests
3. Verify backend response with test script
4. Make sure ports 8000 (backend) and 5500 (frontend) are not blocked

## 💡 Pro Tips

**Tip 1:** Keep browser console open while testing
- Right-click → Inspect → Console tab
- Logs will show exactly what's happening

**Tip 2:** Use weather-test.html for quick diagnosis
- Better than debugging in samarthAI.html
- Can test each component independently

**Tip 3:** Backend is rock-solid
- Verified working 100%
- Frontend integration is what needs verification
- All console logs point to exact issue

## 📞 Still Having Issues?

Check in this order:
1. **Browser Console** → Look for error messages
2. **Network Tab** → Check HTTP requests/responses
3. **Test Script** → Verify backend works: `python test_weather_api.py`
4. **Test HTML** → Use weather-test.html for diagnosis
5. **Backend Logs** → Check terminal where server is running

---

**Status:** Backend 100% working ✓ | Frontend needs verification

See logs in browser console for exact issue!
