print("Testing imports...")
from app import app
print("SUCCESS - All imports complete")
print(f"Registered blueprints: {list(app.blueprints.keys())}")
