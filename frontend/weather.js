// Weather module - handles geolocation and weather data fetching

const BACKEND_URL = 'http://127.0.0.1:8000';

console.log('Weather.js loaded!');

// Get device location and fetch weather on page load
async function initWeather() {
    console.log('initWeather() called');
    try {
        if (!navigator.geolocation) {
            console.warn('Geolocation not supported');
            // Use default location
            useDefaultLocation();
            return;
        }

        // Request geolocation with timeout
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const { latitude, longitude } = position.coords;
                console.log(`✓ Device location: ${latitude}, ${longitude}`);
                await fetchWeatherData(latitude, longitude);
            },
            (error) => {
                console.warn('✗ Geolocation error:', error.message);
                // Use default location as fallback
                console.log('Using fallback location (Kolkata)...');
                useDefaultLocation();
            },
            { timeout: 10000, maximumAge: 60000 }
        );
    } catch (error) {
        console.error('Weather initialization error:', error);
        useDefaultLocation();
    }
}

async function fetchWeatherData(latitude, longitude) {
    try {
        const url = `${BACKEND_URL}/weather?latitude=${latitude}&longitude=${longitude}`;
        console.log(`Fetching weather from: ${url}`);
        
        const response = await fetch(url);
        console.log(`Response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`Backend returned HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('Weather data received:', data);

        if (data.error) {
            console.error('Weather API error:', data.message);
            return;
        }

        updateWeatherCard(data);
    } catch (error) {
        console.error('Failed to fetch weather data:', error);
        // Still try default location if there's an error
        if (latitude !== 22.5726 || longitude !== 88.3639) {
            console.log('Trying fallback location...');
            useDefaultLocation();
        }
    }
}

function updateWeatherCard(data) {
    console.log('Updating weather card with data:', data);
    
    // Update weather button (mini display)
    const weatherMini = document.querySelector('.weather-mini');
    if (weatherMini) {
        const temp = data.temperature;
        const location = data.location.split(',')[0]; // Get just city name
        const newText = `${temp}°C · ${location}`;
        weatherMini.textContent = newText;
        console.log(`✓ Updated weather-mini: ${newText}`);
    } else {
        console.warn('weather-mini element not found');
    }

    // Update weather card top section
    const weatherLoc = document.querySelector('.weather-loc');
    if (weatherLoc) {
        weatherLoc.textContent = data.location;
        console.log(`✓ Updated weather-loc: ${data.location}`);
    }

    const weatherTemp = document.querySelector('.weather-temp');
    if (weatherTemp) {
        weatherTemp.innerHTML = `${data.temperature}°C <span>${data.condition}</span>`;
        console.log(`✓ Updated weather-temp: ${data.temperature}°C ${data.condition}`);
    }

    // Update weather icon based on condition
    updateWeatherIcon(data.condition);

    // Update weather grid
    const weatherGridDivs = document.querySelectorAll('.weather-grid div');
    console.log(`Found ${weatherGridDivs.length} weather grid divs`);
    
    if (weatherGridDivs.length >= 4) {
        weatherGridDivs[0].innerHTML = `<span>Humidity</span><strong>${data.humidity}%</strong>`;
        weatherGridDivs[1].innerHTML = `<span>Rain chance</span><strong>${data.rain_chance}%</strong>`;
        weatherGridDivs[2].innerHTML = `<span>Wind</span><strong>${data.wind_speed} km/h</strong>`;
        weatherGridDivs[3].innerHTML = `<span>Best for spraying</span><strong>${data.spraying_recommendation}</strong>`;
        console.log('✓ Updated weather grid');
    } else {
        console.warn(`Expected 4+ weather grid elements, found ${weatherGridDivs.length}`);
    }

    // Update weather advice
    const weatherAdvice = document.querySelector('.weather-advice');
    if (weatherAdvice) {
        weatherAdvice.textContent = data.advice;
        console.log(`✓ Updated weather-advice: ${data.advice}`);
    }

    console.log('✓ Weather card update complete!');
}

function updateWeatherIcon(condition) {
    const weatherIcon = document.querySelector('.weather-icon');
    if (!weatherIcon) return;

    // Map conditions to SVG paths
    let iconPath = '';
    
    if (condition.toLowerCase().includes('clear') || condition.toLowerCase().includes('sunny')) {
        // Sun icon
        iconPath = `<circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M12 1v6m0 12v6M4.22 4.22l4.24 4.24m5.08 5.08l4.24 4.24M1 12h6m12 0h6m-17.78 7.78l4.24-4.24m5.08-5.08l4.24-4.24" 
                          stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>`;
    } else if (condition.toLowerCase().includes('cloud')) {
        // Cloud icon
        iconPath = `<path d="M7 17.5A4.5 4.5 0 0 1 8 8.6a5.5 5.5 0 0 1 10.6 1.8A4 4 0 0 1 18 18H7.5" 
                          stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>`;
    } else if (condition.toLowerCase().includes('rain')) {
        // Rain icon
        iconPath = `<path d="M7 17.5A4.5 4.5 0 0 1 8 8.6a5.5 5.5 0 0 1 10.6 1.8A4 4 0 0 1 18 18H7.5" 
                          stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M9 19v3M12 19v3M15 19v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>`;
    } else if (condition.toLowerCase().includes('fog')) {
        // Fog icon
        iconPath = `<path d="M3 12h18M3 8h18M3 16h18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>`;
    } else if (condition.toLowerCase().includes('storm') || condition.toLowerCase().includes('thunder')) {
        // Thunder icon
        iconPath = `<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8Z" stroke="currentColor" stroke-width="1.5" 
                          stroke-linecap="round" stroke-linejoin="round"/>`;
    } else if (condition.toLowerCase().includes('snow')) {
        // Snowflake icon
        iconPath = `<path d="M12 2v20M2 12h20M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="1.5" 
                          stroke-linecap="round" stroke-linejoin="round"/>`;
    } else {
        // Default cloud
        iconPath = `<path d="M7 17.5A4.5 4.5 0 0 1 8 8.6a5.5 5.5 0 0 1 10.6 1.8A4 4 0 0 1 18 18H7.5" 
                          stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>`;
    }

    weatherIcon.innerHTML = iconPath;
}

function useDefaultLocation() {
    // Use Kolkata, India as default
    console.log('Fetching weather for default location (Kolkata)...');
    fetchWeatherData(22.5726, 88.3639);
}

// Initialize weather when page loads
console.log('Checking document readyState:', document.readyState);

function startWeatherInit() {
    console.log('Starting weather initialization...');
    // Small delay to ensure DOM is fully ready
    setTimeout(() => {
        console.log('Initializing weather after DOM ready');
        initWeather();
    }, 100);
}

if (document.readyState === 'loading') {
    console.log('Document still loading, adding DOMContentLoaded listener');
    document.addEventListener('DOMContentLoaded', startWeatherInit);
} else {
    console.log('Document already loaded, initializing weather');
    startWeatherInit();
}
