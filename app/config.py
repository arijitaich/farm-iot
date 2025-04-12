import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-dev-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RQ_REDIS_URL = os.getenv("REDIS_URL")
    AES_KEY = os.getenv("AES_KEY").encode()

    # Session config
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production (HTTPS)
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
