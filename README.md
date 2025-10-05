# NASA Weather Prediction App 🌦️
📝 NASA Adverse Weather Likelihood Predictor
This is a full-stack web application built to fulfill the NASA Space Apps Challenge, utilizing live NASA Earth observation data (MERRA-2) and blended with external forecast models (GFS/CPTEC) to predict the likelihood of adverse weather conditions for a user-specified location and date.

✨ Key Features
Live Data Integration: Streams subsetted MERRA-2 (Global Reanalysis) data directly from the NASA Earthdata Cloud (AWS S3).

Future Prediction: Automatically switches to a robust forecast model (NOAA GFS) when querying a future date.

Partner Integration: Includes conditional logic to blend predictions with partner agency data (mock CPTEC/INPE for South America).

Personalized Interface: Provides five calculated risk scores (Hot, Wet, Uncomfortable, etc.) via a user-friendly Streamlit dashboard.

## Branches
- `frontend` → React UI
- `backend` → FastAPI/Flask service
- `data` → NASA API scripts & data logic
- `docs` → Documentation & reports

🔑 Authentication Setup (One-Time Step)
You must create the NASA credentials file that the system needs to access live data.

Locate your User Home Directory: C:\Users\your_username

Create the file: In this directory, create a hidden file named _netrc (note the leading underscore on Windows for reliability).

Add your credentials: Replace the placeholders with your actual NASA Earthdata Login username and password.

Plaintext

machine urs.earthdata.nasa.gov
login <YOUR_EDL_USERNAME>
password <YOUR_EDL_PASSWORD>
🚀 Execution Commands (Two Terminals)
You must open two separate terminals or PowerShell windows.

Terminal 1: Run the Backend API (FastAPI)
This starts the calculator engine that handles the data retrieval.

Navigate to the backend folder.

Command:

Bash

C:\Users\mayuresh\OneDrive\Desktop\NASA\nasa-spaceapps-belagavi-rain-parade-2025\backend\venv\Scripts\python.exe -m uvicorn app:app --reload
(Wait for the Application startup complete message.)

Terminal 2: Run the Frontend (Streamlit)
This launches the web interface that users interact with.

Navigate to the Root Project Directory (the one containing the backend folder).

Command:

Bash

C:\Users\mayuresh\OneDrive\Desktop\NASA\nasa-spaceapps-belagavi-rain-parade-2025\backend\venv\Scripts\python.exe -m streamlit run app_frontend.py
(The app will open automatically in your browser.)