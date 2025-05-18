import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import sys
import importlib.util
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
os.environ['DATABASE_URL'] = 'mysql+pymysql://farmiot:green5en5@localhost:3306/iot_dashboard_v1_04_2025'
# Use the DATABASE_URL from .env (not SQLALCHEMY_DATABASE_URI)
db_url = os.getenv("DATABASE_URL", "sqlite:///../instance/app.db")
if db_url.startswith("sqlite:///"):
    # Convert to absolute path for SQLite
    rel_path = db_url.replace("sqlite:///", "", 1)
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), rel_path))
    db_url = f"sqlite:///{abs_path}"
    # Ensure the directory exists, or print a clear error if not possible
    db_dir = os.path.dirname(abs_path)
    if not os.path.isdir(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except PermissionError:
            print(f"Error: Cannot create database directory '{db_dir}'. Please create it manually and ensure proper permissions.")
            sys.exit(1)

DATABASE_URI = db_url

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

# Import models from app.models
try:
    from app.models import Device, SensorData
except ImportError as e:
    print("Error: Could not import Device and SensorData from app.models:", e)
    sys.exit(1)

def ensure_recent_sensor_data(session, device_id):
    thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
    last_data = session.query(SensorData).filter_by(device_id=device_id).order_by(desc(SensorData.timestamp)).first()
    if last_data and last_data.timestamp < thirty_minutes_ago:
        demo_data = SensorData(
            device_id=device_id,
            timestamp=datetime.utcnow(),
            data=last_data.data
        )
        session.add(demo_data)
        session.commit()
        
def get_weather_and_soil_data(coord_str):
    try:
        lat_str, lon_str = coord_str.split(",")
        lat = float(lat_str.strip())
        lon = float(lon_str.strip())
    except ValueError:
        return {"error": "Invalid coordinate format. Use 'lat,lon'"}

    results = {}

    # 1. Temperature & Humidity from Open-Meteo
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
    )
    weather_response = requests.get(weather_url)

    if weather_response.status_code == 200:
        data = weather_response.json()
        current = data.get("current", {})
        results['temperature_celsius'] = current.get("temperature_2m")
        results['humidity_percent'] = current.get("relative_humidity_2m")
    else:
        results['weather_error'] = f"Weather fetch failed: {weather_response.status_code}"

    # 2. Soil Moisture (0–1cm layer)
    soil_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&daily=soil_moisture_0_1cm_mean&timezone=auto"
    )
    soil_response = requests.get(soil_url)

    if soil_response.status_code == 200:
        soil_data = soil_response.json()
        daily = soil_data.get("daily", {})
        if daily.get("soil_moisture_0_1cm_mean"):
            results['soil_moisture_m3m3'] = daily["soil_moisture_0_1cm_mean"][0]
        else:
            results['soil_moisture_error'] = "No soil moisture data"
    else:
        results['soil_moisture_error'] = f"Soil data fetch failed: {soil_response.status_code}"

    return results

def estimate_temp_hum_moisture(coord_str):
    try:
        lat_str, lon_str = coord_str.split(",")
        lat = float(lat_str.strip())
        lon = float(lon_str.strip())
    except ValueError:
        return {"error": "Invalid coordinate format. Use 'lat,lon'"}

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            current = response.json().get("current", {})
            temp = current.get("temperature_2m")
            rh = current.get("relative_humidity_2m")

            if temp is not None and rh is not None:
                # Empirical estimation
                estimated_soil_moisture = rh / (temp + 1)
                return {
                    "temperature_celsius": temp,
                    "humidity_percent": rh,
                    "estimated_soil_moisture_index": round(estimated_soil_moisture, 2)
                }
            else:
                return {"error": "Temperature or humidity not found"}
        else:
            return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}
    
def predict_next_data_from_history(records):
    # Simple moving average for each field
    n = len(records)
    if n == 0:
        return {}
    avg_temp = sum(r.data.get("temperature", 0) for r in records) / n
    avg_humidity = sum(r.data.get("humidity", 0) for r in records) / n
    avg_moisture = sum(r.data.get("moisture", 0) for r in records) / n
    avg_batper = sum(r.data.get("batper", 0) for r in records) / n
    avg_batvtg = sum(r.data.get("batvtg", 0) for r in records) / n
    return {
        "temperature": round(avg_temp, 2),
        "humidity": round(avg_humidity, 2),
        "moisture": round(avg_moisture, 3),
        "batper": round(avg_batper, 2),
        "batvtg": round(avg_batvtg, 2)
    }

def run_demo_data_worker():
    while True:
        session = Session()
        try:
            devices = session.query(Device).all()
            for device in devices:
                # Get all records for the device
                records = session.query(SensorData).filter_by(device_id=device.device_id).order_by(desc(SensorData.timestamp)).limit(50).all()
                record_count = len(records)
                thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
                last_data = records[0] if records else None
                if not last_data or last_data.timestamp < thirty_minutes_ago:
                    if record_count < 10:
                        # Use estimate_temp_hum_moisture
                        data = estimate_temp_hum_moisture("22.5726,88.3639")
                        temperature = data.get("temperature_celsius", 35.30)
                        humidity = data.get("humidity_percent", 61.00)
                        moisture = data.get("estimated_soil_moisture_index", 0.18)
                        # Use last_data for battery if available, else defaults
                        batper = last_data.data.get("batper", 88) if last_data and isinstance(last_data.data, dict) else 88
                        batvtg = last_data.data.get("batvtg", 4.10) if last_data and isinstance(last_data.data, dict) else 4.10
                    else:
                        # Predict using historical data
                        pred = predict_next_data_from_history(records)
                        temperature = pred["temperature"]
                        humidity = pred["humidity"]
                        moisture = pred["moisture"]
                        batper = pred["batper"]
                        batvtg = pred["batvtg"]
                    demo_url = (
                        f"http://35.244.6.163:5000/data"
                        f"?device_id={device.device_id}"
                        f"&batper={batper}&batvtg={batvtg}&humidity={humidity}&moisture={moisture}&temperature={temperature}"
                    )
                    try:
                        resp = requests.get(demo_url, timeout=10)
                        print(f"Demo data sent for device {device.device_id}: {resp.status_code}")
                    except Exception as e:
                        print(f"Failed to send demo data for device {device.device_id}: {e}")
        except Exception as e:
            print(f"Demo data worker error: {e}")
        finally:
            session.close()
        time.sleep(60)  # Check every 60 seconds


if __name__ == "__main__":
    run_demo_data_worker()
