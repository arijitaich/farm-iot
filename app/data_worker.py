import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Use the DATABASE_URL from .env (not SQLALCHEMY_DATABASE_URI)
DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///../instance/app.db")

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

# Import models using absolute import (not relative)
from app.models import Device, SensorData

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
                ensure_recent_sensor_data(session, device.device_id)
        except Exception as e:
            print(f"Demo data worker error: {e}")
        finally:
            session.close()
        time.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    run_demo_data_worker()
