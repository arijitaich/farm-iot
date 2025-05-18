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


def run_demo_data_worker():
    while True:
        session = Session()
        try:
            devices = session.query(Device).all()
            for device in devices:
                thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
                last_data = session.query(SensorData).filter_by(device_id=device.device_id).order_by(desc(SensorData.timestamp)).first()
                if not last_data or last_data.timestamp < thirty_minutes_ago:
                    # Get weather and soil data
                    data = get_weather_and_soil_data("22.5726,88.3639")
                    
                    # Default values if last_data is missing or doesn't have these fields
                    batper = 88
                    batvtg = 4.10
                    if last_data and isinstance(last_data.data, dict):
                        batper = last_data.data.get("batper", batper)
                        batvtg = last_data.data.get("batvtg", batvtg)
                    
                    humidity = data.get("humidity_percent", 61.00)
                    moisture = data.get("soil_moisture_m3m3", 0.18)
                    temperature = data.get("temperature_celsius", 35.30)

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
