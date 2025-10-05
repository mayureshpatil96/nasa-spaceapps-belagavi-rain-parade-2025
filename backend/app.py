from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # NEW IMPORT
import earthaccess
import xarray as xr 
import numpy as np
from datetime import datetime
import pandas as pd
from geopy.geocoders import Nominatim
import warnings
import requests

# Suppress runtime warnings from NumPy/xarray when dealing with NaN values
warnings.filterwarnings('ignore')

# --- FASTAPI SETUP ---
app = FastAPI()

# --- 🎯 CORS FIX: ALLOWS JAVASCRIPT FRONTEND TO CONNECT ---
origins = [
    "http://127.0.0.1:5500",  # Common Live Server URL for VS Code
    "http://localhost:8000",
    "http://localhost:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------------------------------------------

# --- NASA API CONFIGURATION (M2I1NXASM for hourly data) ---
MERRA2_SHORTNAME = "M2I1NXASM" 
MERRA2_VERSION = "5.12.4" 

# --- CPTEC/INPE CONFIGURATION (Partner Agency Integration) ---
SA_LAT_MIN, SA_LAT_MAX = -56.0, 15.0
SA_LON_MIN, SA_LON_MAX = -82.0, -35.0

# --- GEOLOCATOR SETUP ---
geolocator = Nominatim(user_agent="nasa_weather_app")


@app.get("/")
def home():
    """Simple health check endpoint."""
    return {"message": "NASA Weather Risk API is running. Use /api/risk_by_location to query."}


def is_in_south_america(lat, lon):
    """Simple check to see if the location falls within South America's bounding box."""
    return (SA_LAT_MIN <= lat <= SA_LAT_MAX) and (SA_LON_MIN <= lon <= SA_LON_MAX)

def get_cptec_forecast(city_name: str, date_str: str):
    """
    [MOCK FUNCTION] Simulates fetching forecast data from CPTEC/INPE for blending.
    """
    if "brasil" in city_name.lower() or "sao paulo" in city_name.lower() or "rio de janeiro" in city_name.lower():
         return {
            "temp_c_max": 30.0,
            "wind_km_h_max": 40.0,
            "source": "CPTEC/INPE (MOCK Forecast)"
        }
    return None


def calculate_all_risks(lat: float, lon: float, date_str: str, duration_hours: int, location_name: str = None):
    # 0. CPTEC INTEGRATION CHECK
    cptec_data = None
    if location_name and is_in_south_america(lat, lon):
        cptec_data = get_cptec_forecast(location_name, date_str)
    
    # 1. AUTHENTICATION & TIME SETUP
    auth = earthaccess.login(strategy="netrc") 
    
    start_time = datetime.strptime(f"{date_str}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_time = start_time + pd.Timedelta(hours=duration_hours)
    
    # 2. DATA DISCOVERY & FILTERING
    results = auth.search_data(
        short_name=MERRA2_SHORTNAME,
        version=MERRA2_VERSION,
        temporal=(start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
        point=(lon, lat),
        cloud_hosted=True,
        limit=1
    )

    if not results:
        raise ValueError("No hourly MERRA-2 data found for the specified time/location. Check date range.")

    # 3. DIRECT ACCESS, STREAMING, AND SUBSETTING
    s3_urls = earthaccess.get_s3_urls(results)
    
    ds = xr.open_mfdataset(s3_urls, 
                           engine="netcdf4", 
                           backend_kwargs=dict(storage_options=auth.get_s3_credentials()))
    
    ds_point = ds.sel(lat=lat, lon=lon, method="nearest")
    
    # 4. DATA EXTRACTION AND CONVERSION
    temp_c = ds_point["T2M"].values - 273.15  
    rh_perc = ds_point["RH"].values * 100    
    wind_km_h = np.sqrt(ds_point["U10M"].values**2 + ds_point["V10M"].values**2) * 3.6 
    precip_mm_hr = ds_point["PRECTOT"].values * 3600 * 1000 
    
    total_data_points = len(temp_c)
    if total_data_points == 0:
         raise ValueError("No time-series data points were extracted for the time window. Try adjusting the duration.")

    # 5. RISK CALCULATION AND BLENDING
    
    heat_index = temp_c - 0.55 * (1 - rh_perc / 100) * (temp_c - 14.6)

    HOT_THRESHOLD = 40  
    COLD_THRESHOLD_C = 0 
    WINDY_THRESHOLD = 50 
    WET_THRESHOLD_MM = 5 
    
    hot_likelihood = (np.sum(heat_index > HOT_THRESHOLD) / total_data_points) * 100
    cold_likelihood = (np.sum((temp_c < COLD_THRESHOLD_C) & (wind_km_h > 20)) / total_data_points) * 100
    windy_likelihood = (np.sum(wind_km_h > WINDY_THRESHOLD) / total_data_points) * 100
    wet_likelihood = (np.sum(precip_mm_hr > WET_THRESHOLD_MM) / total_data_points) * 100
    
    # --- BLENDING LOGIC (CPTEC) ---
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
        "query_time_window": f"{start_time.strftime('%Y-%m-%d %H:%M')}Z to {end_time.strftime('%Y-%m-%d %H:%M')}Z",
        "query_location": {"latitude": lat, "longitude": lon},
        "data_points_analyzed": total_data_points,
        "data_source_blended": cptec_data.get('source') if cptec_data else "NASA MERRA-2 (Global)",
        "adverse_risk_likelihoods": {
            "very_hot": round(hot_likelihood, 1),
            "very_cold": round(cold_likelihood, 1),
            "very_windy": round(windy_likelihood, 1),
            "very_wet": round(wet_likelihood, 1),
            "very_uncomfortable": round(uncomfortable_likelihood, 1)
        }
    }


# FASTAPI ENDPOINT: Geocodes user input before running analysis
@app.get("/api/risk_by_location")
def get_risk_by_location(location_name: str, date: str, duration_hours: int = 6):
    try:
        location = geolocator.geocode(location_name)
        
        if not location:
            return {"error": f"Could not find coordinates for: {location_name}"}
            
        lat = location.latitude
        lon = location.longitude
        
        risk_data = calculate_all_risks(lat, lon, date, duration_hours, location_name)
        
        risk_data['query_location']['name'] = location_name
        
        return risk_data

    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}
    #new