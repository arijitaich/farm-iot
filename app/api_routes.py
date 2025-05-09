from flask import Blueprint, request, jsonify
from Crypto.Cipher import AES
import base64
import json
from datetime import datetime
import os
import redis
from rq import Queue
from .worker import insert_sensor_data
from .jwt_utils import encode_token
from .models import User, db
from flask import session
from functools import wraps
from sqlalchemy.exc import IntegrityError  # To handle database integrity errors
from .models import Device  # Assuming a Device model exists
from .models import SensorData  # Import SensorData model


api_bp = Blueprint('api', __name__)
r = redis.from_url(os.getenv("REDIS_URL"))
q = Queue(connection=r)

AES_KEY = os.getenv("AES_KEY").encode()

def pad(s): return s + (16 - len(s) % 16) * ' '

@api_bp.route('/login', methods=['POST'])
def login():
    req = request.json
    email = req.get('email')
    password = req.get('password')

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session['user_email'] = email  # ✅ store in session
        return jsonify({'message': 'Login successful'})
    
    return jsonify({'error': 'Invalid credentials'}), 401

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@api_bp.route('/register-user', methods=['POST'])
def register_user():
    req = request.json
    email = req.get('email')
    password = req.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'User already exists'}), 409

    try:
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        token = encode_token(email)
        return jsonify({'message': 'User registered successfully', 'token': token}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@api_bp.route('/get-devices')
@login_required
def get_devices():
    email = session['user_email']
    try:
        # Fetch devices from the database
        devices = Device.query.all()  # Modify this query if devices are linked to users
        device_list = [
            {
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_type': device.device_type,
                'device_description': device.device_description,
                'device_coordinates': device.device_coordinates,
                'registered_at': device.registered_at.isoformat()
            }
            for device in devices
        ]
        return jsonify({'devices': device_list, 'message': f'Devices for {email}'})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch devices', 'details': str(e)}), 500


@api_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})


@api_bp.route('/register-device', methods=['POST'])
@login_required
def register_device():
    req = request.json
    device_id = req.get('device_id')
    device_name = req.get('device_name')
    device_type = req.get('device_type')
    device_description = req.get('device_description', '')  # Optional field
    device_coordinates = req.get('device_coordinates')  # New field

    # Validate mandatory fields
    if not device_id or not device_name or not device_type or not device_coordinates:
        return jsonify({'error': 'Missing mandatory fields'}), 400

    # Sanitize and validate inputs
    if not device_id.isdigit():
        return jsonify({'error': 'Device ID must contain only numbers'}), 400
    if len(device_name) > 125 or len(device_type) > 125:
        return jsonify({'error': 'Device Name and Type must be less than 125 characters'}), 400

    try:
        # Check for duplicate Device ID
        existing_device = Device.query.filter_by(device_id=device_id).first()
        if existing_device:
            return jsonify({'error': 'Device ID already exists'}), 409

        # Get the logged-in user's ID
        user = User.query.filter_by(email=session['user_email']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Create and save the new device
        new_device = Device(
            device_id=device_id,
            device_name=device_name.strip(),
            device_type=device_type.strip(),
            device_description=device_description.strip(),
            device_coordinates=device_coordinates.strip(),
            user_id=user.id  # Set the user_id to the logged-in user's ID
        )
        db.session.add(new_device)
        db.session.commit()

        return jsonify({'message': 'Device registered successfully'}), 201
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Database integrity error', 'details': str(e.orig)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500


@api_bp.route('/store-sensor-data', methods=['POST'])
def store_sensor_data():
    req = request.json
    device_id = req.get('device_id')
    data = req.get('data')  # Sensor data should be a JSON object

    # Validate mandatory fields
    if not device_id or not data:
        return jsonify({'error': 'Missing device_id or data'}), 400

    try:
        # Check if the device exists
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Create a new SensorData record
        new_sensor_data = SensorData(
            device_id=device_id,
            timestamp=datetime.utcnow(),
            data=data
        )
        db.session.add(new_sensor_data)
        db.session.commit()

        return jsonify({'message': 'Sensor data stored successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred', 'details': str(e)}), 500


@api_bp.route('/get-all-device-data/<device_id>', methods=['GET'])
def get_all_device_data(device_id):
    try:
        # Fetch all sensor data for the device
        records = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).all()
        data_list = [
            {
                'timestamp': record.timestamp.isoformat(),
                'data': record.data
            }
            for record in records
        ]
        return jsonify({'records': data_list})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch device data', 'details': str(e)}), 500
