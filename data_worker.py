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

def run_demo_data_worker():
    while True:
        session = Session()
        try:
            devices = session.query(Device).all()
            for device in devices:
                thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
                last_data = session.query(SensorData).filter_by(device_id=device.device_id).order_by(desc(SensorData.timestamp)).first()
                if not last_data or last_data.timestamp < thirty_minutes_ago:
                    # Compose demo data GET request
                    demo_url = (
                        f"http://35.244.6.163:5000/data"
                        f"?device_id={device.device_id}"
                        f"&batper=88&batvtg=4.10&humidity=61.00&moisture=0.18&temperature=35.30"
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
