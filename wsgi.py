import os
from app import app

# WSGI entry point for production (Render, PythonAnywhere, etc.)
# Run with: gunicorn wsgi:app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
