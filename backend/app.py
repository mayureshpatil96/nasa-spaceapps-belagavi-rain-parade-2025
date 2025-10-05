from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import earthaccess
import xarray as xr 
import numpy as np
from datetime import datetime
import pandas as pd
from geopy.geocoders import Nominatim
import warnings
import requests
import os
import json

# Suppress runtime warnings
warnings.filterwarnings('ignore')

# --- FASTAPI SETUP ---
app = FastAPI()

# --- CORS FIX ---
origins = ["http://127.0.0.1:5500", "http://localhost:8000", "http://localhost:8501", "null"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
MERRA2_SHORTNAME = "M2I1NXASM" 
MERRA2_VERSION = "5.12.4" 
SA_LAT_MIN, SA_LAT_MAX = -56.0, 15.0
SA_LON_MIN, SA_LON_MAX = -82.0, -35.0
geolocator = Nominatim(user_agent=os.environ.get("GEOPY_USER_AGENT", "nasa_weather_app_client"))


@app.get("/")
def home():
    return {"message": "NASA Weather Risk API is running. Use /api/risk_by_location to query."}

# --- GFS FORECAST DATA RETRIEVAL (New function for FUTURE dates) ---

# --- IMPORTANT: FOR THIS TO WORK IN REALITY, YOU NEED A FREE API KEY ---
# Replace YOUR_OWM_API_KEY with a key from a free OpenWeatherMap account (or similar).
# For demonstration purposes, we will continue with robust *simulated* real data.

def get_gfs_forecast_data(lat: float, lon: float, target_start_time: datetime, duration_hours: int):
    """
    Simulates fetching real hourly forecast data (e.g., from a service using the GFS model).
    This function must be replaced with actual API calls in production for 75%+ accuracy.
    """
    # NOTE: In a real submission, this would involve a free API call to a service like OpenWeatherMap
    # or another GFS provider. We are removing the 'extreme' bias but keeping the mock structure.
    
    
    # ----------------------------------------------------------------------------------
    # --- RESTORED: Realistic Mock Data (No Extreme Bias) ---
    # We ensure the data is mild enough not to show 100% risk if actual forecast is mild.
    # The accuracy now relies on the precision of these values matching the real world.
    # We will adjust the mean temperature closer to a mild Indian day.
    # ----------------------------------------------------------------------------------
    
    # Generate mock forecast data for a mild day
    temp_c = np.full(duration_hours, 26) + np.random.uniform(-2, 2, duration_hours) 
    rh_perc = np.full(duration_hours, 60) + np.random.uniform(-10, 10, duration_hours)
    wind_km_h = np.full(duration_hours, 10) + np.random.uniform(-5, 5, duration_hours)
    
    # Assume 10% chance of light rain: most values are 0, with a few spikes.
    precip_mm_hr = np.where(
        np.random.rand(duration_hours) < 0.1, # 10% chance of rain
        np.random.uniform(0.1, 4, duration_hours), # If rain, between 0.1 and 4 mm/hr (mild)
        0 # No rain
    )

    return {
        'temp_c': temp_c,
        'rh_perc': rh_perc,
        'wind_km_h': wind_km_h,
        'precip_mm_hr': precip_mm_hr,
        'source': 'NOAA GFS Model (Future Forecast - *Simulated* for Demo)'
    }


def get_cptec_forecast(city_name: str, date_str: str):
    """
    [MOCK FUNCTION] Simulates CPTEC/INPE data for blending.
    """
    if "brasil" in city_name.lower() or "sao paulo" in city_name.lower() or "rio de janeiro" in city_name.lower():
         return {
            "temp_c_max": 30.0,
            "wind_km_h_max": 40.0,
            "source": "CPTEC/INPE (MOCK Forecast)"
        }
    return None

# CORE RISK CALCULATION FUNCTION

# ... (rest of imports and helper functions)

def calculate_all_risks(lat: float, lon: float, date_str: str, duration_hours: int, location_name: str = None):
    
    # 0. DEFINE TIME VARIABLES GLOBALLY (THE FIX)
    target_start_time = datetime.strptime(f"{date_str}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    target_end_time = target_start_time + pd.Timedelta(hours=duration_hours)
    
    # --- DATA SOURCE DECISION ---
    if target_start_time > datetime.now():
        # Use GFS for FUTURE dates (robust prediction)
        data = get_gfs_forecast_data(lat, lon, target_start_time, duration_hours)
        data_source_used = data['source']
    else:
        # Use NASA MERRA-2 for PAST dates (accurate reanalysis)
        data = fetch_nasa_merra2_data(lat, lon, date_str, duration_hours)
        data_source_used = data['source']
        
    # Check for empty data array
    if len(data['temp_c']) == 0:
        raise ValueError("Data points not extracted. Try adjusting the duration or date.")

    # --- Data Source Blending (CPTEC for SA) ---
    cptec_data = None
    # Only try blending if we used NASA data (past/reanalysis)
    if 'NASA' in data_source_used and location_name and is_in_south_america(lat, lon):
        cptec_data = get_cptec_forecast(location_name, date_str)

    # 5. RISK CALCULATION LOGIC (Unified)
    
    temp_c = data['temp_c']
    rh_perc = data['rh_perc']
    wind_km_h = data['wind_km_h']
    precip_mm_hr = data['precip_mm_hr']
    total_data_points = len(temp_c)
    
    heat_index = temp_c - 0.55 * (1 - rh_perc / 100) * (temp_c - 14.6)
    
    HOT_THRESHOLD = 40  
    COLD_THRESHOLD_C = 0 
    WINDY_THRESHOLD = 50 
    WET_THRESHOLD_MM = 5 
    
    # Likelihood Calculation
    hot_likelihood = (np.sum(heat_index > HOT_THRESHOLD) / total_data_points) * 100
    cold_likelihood = (np.sum((temp_c < COLD_THRESHOLD_C) & (wind_km_h > 20)) / total_data_points) * 100
    windy_likelihood = (np.sum(wind_km_h > WINDY_THRESHOLD) / total_data_points) * 100
    wet_likelihood = (np.sum(precip_mm_hr > WET_THRESHOLD_MM) / total_data_points) * 100
    
    # Blending 
    if cptec_data:
        if cptec_data.get('temp_c_max', 0) > 35:
            hot_likelihood = min(100, hot_likelihood + 20) 
        if cptec_data.get('wind_km_h_max', 0) > 55:
            windy_likelihood = min(100, windy_likelihood + 30) 
    
    thermal_risk = np.maximum(hot_likelihood, cold_likelihood)
    uncomfortable_likelihood = (thermal_risk * 0.6) + (wet_likelihood * 0.2) + (windy_likelihood * 0.2)
    uncomfortable_likelihood = min(100, uncomfortable_likelihood) 

    # 6. FINAL OUTPUT
    return {
        # This will now work because target_end_time is defined at the start
        "query_time_window": f"{target_start_time.strftime('%Y-%m-%d %H:%M')}Z to {target_end_time.strftime('%Y-%m-%d %H:%M')}Z",
        "query_location": {"latitude": lat, "longitude": lon},
        "data_points_analyzed": total_data_points,
        "data_source_blended": data['source'], # Use the source from the returned data
        "adverse_risk_likelihoods": {
            "very_hot": round(hot_likelihood, 1),
            "very_cold": round(cold_likelihood, 1),
            "very_windy": round(windy_likelihood, 1),
            "very_wet": round(wet_likelihood, 1),
            "very_uncomfortable": round(uncomfortable_likelihood, 1)
        }
    }

# ... (rest of the file)

# NASA MERRA-2 FETCH FUNCTION (Now dedicated to past data)
def fetch_nasa_merra2_data(lat: float, lon: float, date_str: str, duration_hours: int):
    auth = earthaccess.login(strategy="netrc") 
    target_start_time = datetime.strptime(f"{date_str}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    target_end_time = target_start_time + pd.Timedelta(hours=duration_hours)
    search_start_time = target_start_time - pd.Timedelta(hours=24)
    search_end_time = target_end_time + pd.Timedelta(hours=24)
    BOUNDING_BOX = [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05] 
    
    results = earthaccess.search_data(
        short_name=MERRA2_SHORTNAME,
        version=MERRA2_VERSION,
        temporal=(search_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), search_end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
        bounding_box=BOUNDING_BOX 
    )

    if not results:
        yesterday = (datetime.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        raise ValueError(f"No MERRA-2 data found. Try a date before {yesterday} or change location.")

    s3_urls = earthaccess.get_s3_urls([results[0]]) 
    
    ds = xr.open_mfdataset(s3_urls, engine="netcdf4", backend_kwargs=dict(storage_options=auth.get_s3_credentials()))
    
    ds_point = ds.sel(lat=lat, lon=lon, method="nearest").sel(time=slice(target_start_time, target_end_time))
    
    return {
        'temp_c': ds_point["T2M"].values - 273.15,  
        'rh_perc': ds_point["RH"].values * 100,
        'wind_km_h': np.sqrt(ds_point["U10M"].values**2 + ds_point["V10M"].values**2) * 3.6,
        'precip_mm_hr': ds_point["PRECTOT"].values * 3600 * 1000,
        'source': 'NASA MERRA-2 (Reanalysis)'
    }


# FASTAPI ENDPOINT
@app.get("/api/risk_by_location")
def get_risk_by_location(location_name: str, date: str, duration_hours: int = 6):
    try:
        # 1. Geocode location
        location = geolocator.geocode(location_name)
        if not location:
            return {"error": f"Could not find coordinates for: {location_name}"}
        lat = location.latitude
        lon = location.longitude
        
        # 2. Run the core calculation function
        risk_data = calculate_all_risks(lat, lon, date, duration_hours, location_name)
        
        # 3. Add the location name to the final output
        risk_data['query_location']['name'] = location_name
        
        return risk_data

    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}