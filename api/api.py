# api/index.py
import sys
import os

# Ensure the inner DocuMorph directory is on sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DocuMorph"))

from DocuMorph import app as application  # Import the Flask app

# Vercel expects a variable called "app" or "application"
app = application
