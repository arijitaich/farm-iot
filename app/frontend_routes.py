from flask import Blueprint, render_template
from .jwt_utils import login_required, token_required

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
@token_required
def device_view(device_id):
    return render_template("device_view.html", device=[device_id, "Mock Device", "Type A", "Demo Description"], data_points={"temp": 25, "volt": 3.7})
