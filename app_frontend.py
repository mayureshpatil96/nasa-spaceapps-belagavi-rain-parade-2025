import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
import random
import os

# --- FASTAPI SERVER URL ---
# The Streamlit frontend will call your FastAPI backend running on port 8000
FASTAPI_URL = "http://127.0.0.1:8000/api/risk_by_location"

# --- STREAMLIT PAGE SETUP ---
st.set_page_config(layout="wide")
st.title("🛰️ NASA Adverse Weather Likelihood Predictor")
st.markdown("A personalized app using **NASA MERRA-2 data** blended with partner data to predict risks for your outdoor event.")
st.markdown("---")

st.sidebar.header("Event Details")

# Input widgets
location_name = st.sidebar.text_input("Location (City, Country)", "Sao Paulo, Brasil") 

# --- FIX for Data Latency: Set default date to a stable past date (e.g., 3 days ago)
default_date = date.today() - timedelta(days=3)
event_date = st.sidebar.date_input("Event Start Date", default_date) 
duration = st.sidebar.slider("Event Duration (Hours)", 1, 24, 6)

# --- RISK COLORS AND ICONS ---
RISK_ICONS = {
    "very_hot": "🔥", "very_cold": "❄️", 
    "very_windy": "💨", "very_wet": "🌧️", 
    "very_uncomfortable": "😟"
}

if st.sidebar.button("Calculate Risk"):
    
    # 1. Prepare Query Parameters
    params = {
        "location_name": location_name,
        "date": event_date.strftime("%Y-%m-%d"),
        "duration_hours": duration
    }
    
    st.info(f"Querying weather data for: **{location_name}** on **{event_date}** for {duration} hours...")
    
    try:
        # 2. Call the Backend API (FastAPI)
        response = requests.get(FASTAPI_URL, params=params, timeout=60)
        
        if response.status_code != 200:
            error_data = response.json() 
            st.error(f"API Error (Status {response.status_code}): {error_data.get('error', 'Unknown failure.')}")
            st.warning("Please verify your backend terminal for detailed error logs (e.g., authentication failure or invalid date).")
            st.stop()
            
        data = response.json()
        
        if 'error' in data:
            st.error(f"Data Processing Error: {data['error']}")
            st.stop()

        # 3. Process and Display Results
        
        # Display location info
        st.header(f"Forecasted Risks for {data['query_location'].get('name', 'Point')}")
        st.subheader(f"Window: {data['query_time_window']}")
        st.caption(f"Source: {data['data_source_blended']} (Analyzed {data['data_points_analyzed']} hourly data points)")
        
        risk_dict = data['adverse_risk_likelihoods']
        risk_data_list = []
        cols = st.columns(5)
        
        for i, (condition, likelihood) in enumerate(risk_dict.items()):
            
            # Format name and get icons
            display_name = condition.replace('_', ' ').title().replace('Very ', '')
            icon = RISK_ICONS.get(condition, '❓')
            
            risk_data_list.append({
                'Condition': display_name,
                'Likelihood (%)': likelihood,
            })
            
            # Display gauge in a column
            with cols[i]:
                st.metric(label=f"{icon} {display_name}", 
                          value=f"{likelihood:.1f}%", 
                          delta_color="off")
                
                # Simple progress bar visualization
                st.progress(likelihood / 100.0)

        st.markdown("---")
        
        # Display summary data in a table
        st.subheader("Detailed Risk Summary")
        st.dataframe(
            pd.DataFrame(risk_data_list).set_index('Condition'), 
            use_container_width=True
        )
            
    except requests.exceptions.ConnectionError:
        st.error("🚨 Connection Error: The FastAPI backend server is not running or is unreachable.")
        st.caption(f"Ensure you start the backend in a separate terminal from the `backend` folder: `.\\venv\\Scripts\\uvicorn app:app --reload`")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")