from fastapi import FastAPI
import earthaccess
from netCDF4 import Dataset
import numpy as np

app = FastAPI()

@app.get("/")
def home():
    return {"message": "NASA Weather Risk API is running"}

@app.get("/api/risk")
def get_risk(lat: float, lon: float, date: str):
    try:
        auth = earthaccess.login(strategy="_netrc")

        # Search NASA MERRA-2 dataset for the given date
        results = earthaccess.search_data(
            short_name="M2TMNXSLV",
            version="5.12.4",
            temporal=(date, date),
            cloud_hosted=True,
            count=1
        )

        if not results:
            return {"error": "No dataset found for the given date."}

        # Download dataset locally (avoid DAP errors)
        file_path = earthaccess.download(results[0], "./data")[0]
        ds = Dataset(file_path)

        temp = np.mean(ds.variables["T2M"][:]) - 273.15  # Kelvin → Celsius
        ds.close()

        # Simple risk calculation
        risk = round((temp - 25) / 10, 2)

        return {
            "date": date,
            "latitude": lat,
            "longitude": lon,
            "avg_temperature": round(float(temp), 2),
            "risk_index": risk
        }

    except Exception as e:
        return {"error": str(e)}
