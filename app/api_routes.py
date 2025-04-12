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


api_bp = Blueprint('api', __name__)
r = redis.from_url(os.getenv("REDIS_URL"))
q = Queue(connection=r)

AES_KEY = os.getenv("AES_KEY").encode()

def pad(s): return s + (16 - len(s) % 16) * ' '

def decrypt_data(encrypted_text):
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    decoded = base64.b64decode(encrypted_text)
    decrypted = cipher.decrypt(decoded)
    return decrypted.decode().strip()

@api_bp.route('/data', methods=['GET'])
def ingest_data():
    encrypted_payload = request.args.get('payload')
    if not encrypted_payload:
        return jsonify({'error': 'Missing payload'}), 400
    try:
        payload = json.loads(decrypt_data(encrypted_payload))
        device_id = payload.get('device_id')
        timestamp = payload.get('timestamp')
        data = payload.get('data')
        ts = datetime.fromisoformat(timestamp)
        if abs((datetime.utcnow() - ts).total_seconds()) > 300:
            return jsonify({'error': 'Stale timestamp'}), 400
        q.enqueue(insert_sensor_data, {
            'device_id': device_id,
            'timestamp': timestamp,
            'data': data
        })
        return jsonify({'status': 'accepted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    # Dummy response for now, or pull devices from DB
    return jsonify({
        'devices': [],
        'message': f'Devices for {email}'
    })


@api_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})
