<<<<<<< HEAD
# farm-iot
=======
# 🌾 Farm-IoT Platform

A production-ready Flask-based IoT platform for securely ingesting, storing, and managing device data — with support for user registration, login, and device dashboards.

---

## 🔧 Features

- 🔐 Secure user login/signup with session-based authentication
- 🌐 REST API endpoints for encrypted IoT data ingestion
- 🧠 Background job processing with Redis + RQ
- 📦 MySQL as primary data store
- 📊 Dashboard UI with TailwindCSS
- 🛡 AES-encrypted payload handling
- 📍 Device registration, listing, and deletion

---

## 📁 Project Structure

farm-iot/ 
├── app/ 
│ ├── init.py # App factory & setup 
│ ├── api_routes.py # All API endpoints 
│ ├── frontend_routes.py # HTML-rendered routes 
│ ├── models.py # SQLAlchemy models 
│ ├── config.py # App config 
│ ├── jwt_utils.py # Session auth utils 
│ └── worker.py # Background job handler 
├── templates/ 
│ ├── login_signup.html 
│ └── dashboard.html 
├── main.py # App entry point 
├── .env # Env vars (not committed) 
└── README.md


---

## ⚙️ Requirements

- Python 3.11+
- MySQL Server
- Redis
- Virtualenv

---

## 🚀 Setup Guide

### 1. Clone the repository

git clone https://github.com/your-org/farm-iot.git
cd farm-iot

### 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # for Linux/macOS
# OR
.venv\Scripts\activate     # for Windows

### 3. Install dependencies
pip install -r requirements.txt

### 4. Configure environment variables
Create a .env file in the root directory:

# .env
SECRET_KEY=some_super_secret_key
DATABASE_URL=mysql+pymysql://root:yourpassword@127.0.0.1:3306/farmiot
REDIS_URL=redis://localhost:6379/0
AES_KEY=your16bytekey__  # Must be exactly 16 characters

### 5. Setup MySQL Database
mysql -u root -p
CREATE DATABASE farmiot;
EXIT;

Then run the app to auto-create tables:
python3 main.py

### 6. Start Redis Server
redis-server

### 7. Run the RQ Worker
rq worker --url redis://localhost:6379/0


### ✅ Run the Flask App
python3 main.py
Visit: http://127.0.0.1:5000

### 🔐 Login & Test
Register a user

Login


### 🔒 Security Notes
AES encryption uses AES_KEY for payloads.
Flask sessions are secured with SECRET_KEY.

### 🤝 Contributing
Pull requests and feedback welcome. For major changes, please open an issue first.

### 📜 License
MIT License – use it, modify it, improve it.
>>>>>>> 0f25841 (Initial commit: Project structure with Flask app factory, user auth, MySQL models, and Redis queue setup)
