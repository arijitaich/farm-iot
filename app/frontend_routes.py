from flask import Blueprint, render_template, request, jsonify, session
from .jwt_utils import login_required, token_required
from .models import Device, User, SensorData

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/')
def index():
    return render_template("login_register.html")

@frontend_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

@frontend_bp.route('/profile_settings')
@token_required
def profile_settings():
    return render_template("profile_settings.html")

@frontend_bp.route('/device_view/<device_id>')
@login_required  # Use session-based authentication
def device_view(device_id):
    email = session.get('user_email')  # Get the logged-in user's email
    try:
        # Fetch the device from the database
        device = Device.query.filter_by(device_id=device_id).first()

        # Check if the device exists
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Check if the device belongs to the logged-in user
        user = User.query.filter_by(email=email).first()
        if not user or device not in user.devices:  # Assuming a relationship exists
            return jsonify({'error': 'Unauthorized access to this device'}), 403

        # Fetch the latest data points for the device
        data_points = {}
        latest_sensor_data = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).first()
        if latest_sensor_data:
            data_points = latest_sensor_data.data

        # Pass the device data to the template
        return render_template(
            "device_view.html",
            device=[device.device_id, device.device_name, device.device_type, device.device_description],
            data_points=data_points
        )
    except Exception as e:
        return jsonify({'error': 'An error occurred', 'details': str(e)}), 500
