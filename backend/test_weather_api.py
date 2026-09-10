#!/usr/bin/env python3
"""Quick test script for weather API"""

import asyncio
import httpx

async def test_backend():
    """Test weather API endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            # Test health
            print("Testing /health endpoint...")
            health_resp = await client.get("http://127.0.0.1:8000/health")
            print(f"Health status: {health_resp.status_code}")
            print(f"Health response: {health_resp.json()}\n")
            
            # Test weather
            print("Testing /weather endpoint...")
            weather_resp = await client.get(
                "http://127.0.0.1:8000/weather",
                params={"latitude": 22.5726, "longitude": 88.3639}
            )
            print(f"Weather status: {weather_resp.status_code}")
            import json
            print(f"Weather response:\n{json.dumps(weather_resp.json(), indent=2)}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backend())
