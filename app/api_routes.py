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
from .models import Chart  # Import Chart model
from .models import Alert  # Import Alert model
from .models import Notification  # Import Notification model


api_bp = Blueprint('api', __name__)
r = redis.from_url(os.getenv("REDIS_URL"))
q = Queue(connection=r)

DEVICE_NOT_FOUND_MSG = 'Device not found'

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
            return jsonify({'error': DEVICE_NOT_FOUND_MSG}), 404
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


@api_bp.route('/device_data/<device_id>', methods=['GET'])
@login_required
def get_device_data(device_id):
    try:
        # Fetch device information
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Fetch the latest sensor data for the device
        latest_data = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).first()
        data_points = latest_data.data if latest_data else {}

        # Extract parameter names from the data points
        params = list(data_points.keys()) if isinstance(data_points, dict) else []

        # Prepare the response
        response = {
            'device_id': device.device_id,
            'device_name': device.device_name,
            'device_type': device.device_type,
            'device_description': device.device_description,
            'data_points': data_points,
            'params': params
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch device data', 'details': str(e)}), 500


@api_bp.route('/device_data_last_20/<device_id>', methods=['GET'])
@login_required
def get_last_20_device_data(device_id):
    try:
        # Fetch the last 20 sensor data records for the device
        records = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).limit(20).all()
        data_list = [
            {
                'time': record.timestamp.isoformat(),
                'data': record.data
            }
            for record in records
        ]
        return jsonify(data_list)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch device data', 'details': str(e)}), 500


@api_bp.route('/device_data_range/<device_id>', methods=['GET'])
@login_required
def get_device_data_range(device_id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Validate date inputs
    if not start_date or not end_date:
        return jsonify({'error': 'Missing start_date or end_date'}), 400

    try:
        # Parse dates
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

        # Fetch sensor data within the date range
        records = SensorData.query.filter(
            SensorData.device_id == device_id,
            SensorData.timestamp >= start_date,
            SensorData.timestamp <= end_date
        ).order_by(SensorData.timestamp.asc()).all()

        data_list = [
            {
                'time': record.timestamp.isoformat(),
                'data': record.data
            }
            for record in records
        ]

        return jsonify(data_list)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD).'}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to fetch device data', 'details': str(e)}), 500


@api_bp.route('/device_data_all/<device_id>', methods=['GET'])
@login_required
def get_all_device_data_records(device_id):
    try:
        # Fetch all sensor data records for the device
        records = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.asc()).all()
        data_list = [
            {
                'time': record.timestamp.isoformat(),
                'data': record.data
            }
            for record in records
        ]
        return jsonify(data_list)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch all device data', 'details': str(e)}), 500


@api_bp.route('/data', methods=['GET'])
def demo_webhook():
    device_id = request.args.get('device_id')
    data = {key: request.args.get(key) for key in request.args if key != 'device_id'}

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

        return jsonify({'message': 'Demo data pushed successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred', 'details': str(e)}), 500


@api_bp.route('/get-charts/<device_id>', methods=['GET'])
@login_required
def get_charts(device_id):
    try:
        # Fetch saved chart configurations for the device
        charts = Chart.query.filter_by(device_id=device_id).order_by(Chart.position.asc()).all()
        chart_list = [
            {
                'id': chart.id,
                'chart_name': chart.chart_name,
                'chart_type': chart.chart_type,
                'x_axis_params': chart.x_axis_params,
                'y_axis_params': chart.y_axis_params,
                'is_live': chart.is_live,
                'position': chart.position
            }
            for chart in charts
        ]
        return jsonify({'charts': chart_list})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch chart configurations', 'details': str(e)}), 500


@api_bp.route('/create-chart', methods=['POST'])
@login_required
def create_chart():
    req = request.json
    device_id = req.get('device_id')
    chart_name = req.get('chart_name')
    chart_type = req.get('chart_type')
    x_axis_params = req.get('x_axis_params')
    y_axis_params = req.get('y_axis_params')
    is_live = req.get('is_live', False)
    position = req.get('position')

    # Validate mandatory fields
    if not device_id or not chart_name or not chart_type or not x_axis_params or not y_axis_params or position is None:
        return jsonify({'error': 'Missing mandatory fields'}), 400

    try:
        # Check if the device exists
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Create and save the new chart configuration
        new_chart = Chart(
            device_id=device_id,
            chart_name=chart_name.strip(),
            chart_type=chart_type.strip(),
            x_axis_params=x_axis_params,
            y_axis_params=y_axis_params,
            is_live=is_live,
            position=position
        )
        db.session.add(new_chart)
        db.session.commit()

        return jsonify({'message': 'Chart created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the chart', 'details': str(e)}), 500


@api_bp.route('/delete-chart/<chart_id>', methods=['POST'])
@login_required
def delete_chart(chart_id):
    try:
        # Fetch the chart by ID
        chart = Chart.query.filter_by(id=chart_id).first()
        if not chart:
            return jsonify({'error': 'Chart not found'}), 404

        # Delete the chart
        db.session.delete(chart)
        db.session.commit()

        return jsonify({'message': 'Chart deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the chart', 'details': str(e)}), 500


@api_bp.route('/get-alerts/<device_id>', methods=['GET'])
@login_required
def get_alerts(device_id):
    try:
        # Fetch alerts for the specified device
        alerts = Alert.query.filter_by(device_id=device_id).order_by(Alert.timestamp.desc()).all()
        alert_list = [
            {
                'id': alert.id,
                'name': alert.alert_type,
                'parameter': alert.message,
                'timestamp': alert.timestamp.isoformat()
            }
            for alert in alerts
        ]
        return jsonify({'alerts': alert_list})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch alerts', 'details': str(e)}), 500


@api_bp.route('/create_alert', methods=['POST'])
@login_required
def create_alert():
    req = request.json
    device_id = req.get('device_id')
    alert_name = req.get('alert_name')
    alert_parameter = req.get('alert_parameter')
    alert_value = req.get('alert_value')
    alert_gate = req.get('alert_gate')

    # Validate mandatory fields
    if not device_id or not alert_name or not alert_parameter or not alert_value or not alert_gate:
        return jsonify({'error': 'Missing mandatory fields'}), 400

    try:
        # Check if the device exists
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Create and save the new alert
        new_alert = Alert(
            device_id=device_id,
            alert_type=alert_name.strip(),
            message=f"{alert_parameter} {alert_gate} {alert_value}"
        )
        db.session.add(new_alert)
        db.session.commit()

        return jsonify({'message': 'Alert created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the alert', 'details': str(e)}), 500


@api_bp.route('/delete_alert/<alert_id>', methods=['POST'])
@login_required
def delete_alert(alert_id):
    try:
        # Fetch the alert by ID
        alert = Alert.query.filter_by(id=alert_id).first()
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404

        # Delete the alert
        db.session.delete(alert)
        db.session.commit()

        return jsonify({'message': 'Alert deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the alert', 'details': str(e)}), 500


@api_bp.route('/get-notifications/<device_id>', methods=['GET'])
@login_required
def get_notifications(device_id):
    try:
        # Fetch notifications for the specified device
        notifications = Notification.query.filter_by(device_id=device_id).order_by(Notification.timestamp.desc()).all()
        unseen_count = Notification.query.filter_by(device_id=device_id, seen=False).count()

        notification_list = [
            {
                'id': notification.id,
                'alert_name': notification.alert_name,
                'message': notification.message,
                'time': notification.timestamp.isoformat(),
                'seen': notification.seen
            }
            for notification in notifications
        ]

        return jsonify({'notifications': notification_list, 'unseen_count': unseen_count})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch notifications', 'details': str(e)}), 500


@api_bp.route('/mark-notifications-seen/<device_id>', methods=['POST'])
@login_required
def mark_notifications_seen(device_id):
    try:
        # Update all unseen notifications for the device to seen
        Notification.query.filter_by(device_id=device_id, seen=False).update({'seen': True})
        db.session.commit()

        return jsonify({'message': 'All notifications marked as seen'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to mark notifications as seen', 'details': str(e)}), 500


@api_bp.route('/overall-stats', methods=['GET'])
@login_required
def overall_stats():
    try:
        # Fetch total devices
        total_devices = Device.query.count()

        # Fetch active devices (devices with data in the last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_devices = (
            db.session.query(Device)
            .join(SensorData, Device.device_id == SensorData.device_id)
            .filter(SensorData.timestamp >= thirty_days_ago)
            .distinct(Device.device_id)
            .count()
        )

        # Calculate inactive devices
        inactive_devices = total_devices - active_devices

        # Return the stats
        return jsonify({
            'total_devices': total_devices,
            'active_devices': active_devices,
            'inactive_devices': inactive_devices
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch overall stats', 'details': str(e)}), 500
