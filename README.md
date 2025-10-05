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

🔑 Step 1: Set Up Your NASA Login (CRITICAL)
Your application needs permission to talk to NASA's servers. You do this by creating a special file in your main user folder.

Find Your Folder: Go to your user's home directory: C:\Users\your_username

Create the File: In that folder, create a new hidden file named _netrc (Note the underscore _).

Add Your Credentials: Paste your NASA Earthdata Login (EDL) info inside the file.

Plaintext

machine urs.earthdata.nasa.gov
login <YOUR_EDL_USERNAME>
password <YOUR_EDL_PASSWORD>

<br>
🚀 Step 2: Run the Project (Two Terminal Windows)
You must open two separate terminals. You will be using the long, secure path to the python.exe file inside your environment for both commands to avoid errors.

Terminal 1: Start the Calculator (API Backend)
This launches the program that runs the weather math.

Navigate to the backend folder.

Run Command:

Bash

C:\Users\mayuresh\OneDrive\Desktop\NASA\nasa-spaceapps-belagavi-rain-parade-2025\backend\venv\Scripts\python.exe -m uvicorn app:app --reload
Wait until you see the message: Application startup complete.


<br>

Terminal 2: Start the Website (Frontend App)
This launches the web page you interact with.

Navigate to the project's Root Directory (where app_frontend.py is).

Run Command:

Bash

C:\Users\mayuresh\OneDrive\Desktop\NASA\nasa-spaceapps-belagavi-rain-parade-2025\backend\venv\Scripts\python.exe -m streamlit run app_frontend.py
This will automatically open the application in your web browser.