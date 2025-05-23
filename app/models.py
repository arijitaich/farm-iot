from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

CASCADE_OPTION = "all, delete-orphan"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    devices = db.relationship('Device', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(255), unique=True, nullable=False)
    device_name = db.Column(db.String(255))
    device_type = db.Column(db.String(255))
    device_description = db.Column(db.Text)
    device_coordinates = db.Column(db.String(255))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sensor_data = db.relationship('SensorData', backref='device', lazy=True, cascade=CASCADE_OPTION)
    charts = db.relationship('Chart', backref='device', lazy=True, cascade=CASCADE_OPTION)
    notifications = db.relationship('Notification', backref='device', lazy=True, cascade=CASCADE_OPTION, foreign_keys='Notification.device_id')
    alerts = db.relationship('Alert', backref='device', lazy=True, cascade=CASCADE_OPTION, foreign_keys='Alert.device_id')

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(255), db.ForeignKey('device.device_id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    data = db.Column(db.JSON)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(255), db.ForeignKey('device.device_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    alert_type = db.Column(db.String(100))
    message = db.Column(db.Text)

    notifications = db.relationship('Notification', backref='alert', lazy=True, cascade=CASCADE_OPTION)

class Chart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(255), db.ForeignKey('device.device_id'), nullable=False)
    chart_name = db.Column(db.String(255), nullable=False)
    chart_type = db.Column(db.String(50), nullable=False)
    x_axis_params = db.Column(db.JSON, nullable=False)
    y_axis_params = db.Column(db.JSON, nullable=False)
    is_live = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('alert.id'), nullable=False)
    device_id = db.Column(db.String(255), db.ForeignKey('device.device_id'), nullable=False)
    alert_name = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    seen = db.Column(db.Boolean, default=False)
