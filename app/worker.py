from . import db
from .models import SensorData, Alert
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

def insert_sensor_data(payload):
    try:
        sensor = SensorData(
            device_id=payload['device_id'],
            timestamp=datetime.fromisoformat(payload['timestamp']),
            data=payload['data']
        )
        db.session.add(sensor)
        db.session.commit()

        # Example: dynamic alert check (voltage check)
        if 'voltage' in payload['data'] and payload['data']['voltage'] < 3.3:
            alert = Alert(
                device_id=sensor.device_id,
                alert_type="Low Voltage",
                message=f"Voltage dropped to {payload['data']['voltage']}V"
            )
            db.session.add(alert)
            db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()
        print("DB Error:", str(e))
