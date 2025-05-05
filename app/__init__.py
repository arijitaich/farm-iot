import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Import Flask-Migrate
from .config import Config

db = SQLAlchemy()
migrate = Migrate()  # Initialize Flask-Migrate

def create_app():
    # Ensure templates folder is found correctly
    TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    iot_app = Flask(__name__, template_folder=TEMPLATE_DIR)

    # Load config from .env and config.py
    iot_app.config.from_object(Config)

    # Initialize database
    db.init_app(iot_app)
    migrate.init_app(iot_app, db)  # Bind Flask-Migrate to the app and db

    # Register all blueprints
    from .api_routes import api_bp
    from .frontend_routes import frontend_bp
    from .error_handlers import error_bp

    iot_app.register_blueprint(api_bp)
    iot_app.register_blueprint(frontend_bp)
    iot_app.register_blueprint(error_bp)

    # Automatically create tables if they don't exist
    with iot_app.app_context():
        from app import models  # This ensures all models are loaded
        db.create_all()
    
    return iot_app
