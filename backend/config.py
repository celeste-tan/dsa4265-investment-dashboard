# === config.py ===
"""
Centralised configuration file for environment variables, API keys,
and default app behaviour.
"""

# -----------------------------
# Imports
# -----------------------------
from dotenv import load_dotenv
import os
from pathlib import Path

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()

# -----------------------------
# Configuration Class
# -----------------------------
class Config:
    """
    Configuration object used by Flask app and utilities.
    """

    # -------------------------
    # Database Configuration
    # -------------------------
    DATABASE_PATH = str(Path(__file__).parent / 'data' / 'investment.db')

    # -------------------------
    # API Keys & Auth
    # -------------------------
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ESG_API_TOKEN = os.getenv("ESG_API_TOKEN")
    API_ID = os.getenv("API_ID")           # Telegram API ID
    API_HASH = os.getenv("API_HASH")       # Telegram API Hash
    PHONE = os.getenv("PHONE")             # Telegram phone number

    # -------------------------
    # App Defaults
    # -------------------------
    DEFAULT_PERIOD = "1y"                  # Default stock chart period
    DEFAULT_NEWS_DAYS = 30                 # Default window for media sentiment
    NEWS_LOOKBACK_DAYS = 30                # How far back to scrape news headlines
