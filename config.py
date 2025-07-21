# config.py - Configuration settings for the YouTube to Text converter

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# YouTube Download Settings
RECENT_HOURS = int(os.environ.get('RECENT_HOURS', 48))  # Consider videos from last 48 hours as recent
MAX_VIDEOS_TO_CHECK = int(os.environ.get('MAX_VIDEOS_TO_CHECK', 2))  # Number of recent videos to check
AUDIO_FORMAT = os.environ.get('AUDIO_FORMAT', 'mp3')
AUDIO_QUALITY = os.environ.get('AUDIO_QUALITY', '192')

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_AUDIO_DIR = os.path.join(BASE_DIR, 'temp_audio')
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, 'transcripts')

# Gemini API Settings
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyAkUM4-BpeC6t7CUs0nf1YhVyRyxSa3a2U')
if GEMINI_API_KEY == 'your-api-key-here':
    print("WARNING: GEMINI_API_KEY not set in environment variables!")

# Flask Settings
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('FLASK_PORT', 5050))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

# File naming
TRANSCRIPT_EXTENSION = '.txt'

# Create directories if they don't exist
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)