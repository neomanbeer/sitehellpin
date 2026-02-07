"""
Run the app locally with SQLite (no PostgreSQL needed).
Usage: python run_local.py
Then open http://127.0.0.1:5000
"""
import os
# Use SQLite when DATABASE_URL is not set (e.g. local dev)
if not os.environ.get("DATABASE_URL"):
    os.environ.setdefault("FLASK_DEBUG", "1")
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
