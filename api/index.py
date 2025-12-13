"""
Vercel serverless function entry point for Flask app
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import Flask app
from backend.app import create_app

# Create Flask app instance
app = create_app()

# Export app for Vercel
# Vercel Python runtime will automatically handle WSGI apps
__all__ = ['app']
