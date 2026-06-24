"""
WSGI entry point for PythonAnywhere.
To use this file:
1. Upload your project to /home/<username>/mysite/ on PythonAnywhere
2. Go to the "Web" tab, click on your web app
3. Edit the WSGI configuration file (link at the top of the page)
4. Replace the entire content with this file's content
5. Update <username> below with your actual PythonAnywhere username
6. Click "Save" then "Reload" your web app
"""
import sys
import os

# === CHANGE THIS TO YOUR USERNAME ===
USERNAME = "VOTRE_USERNAME"

# Add the project directory to sys.path
project_home = f"/home/{USERNAME}/mysite"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtualenv if you have one (optional)
# PA provides a pre-configured virtualenv, usually auto-activated.
# If you need to point to a specific venv:
#   venv_path = f"/home/{USERNAME}/.virtualenvs/mon-env/lib/python3.11/site-packages"
#   sys.path.insert(0, venv_path)

# Set environment variable for production
os.environ["PRODUCTION"] = "1"
os.environ["SECRET_KEY"] = "barham-secret-key-prod-2024"

from app import app as application
