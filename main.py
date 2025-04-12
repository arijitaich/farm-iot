import sys
import os
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()
print("✅ Flask app initialized. Tables are created if missing.")

if __name__ == '__main__':
    app.run(debug=True)
