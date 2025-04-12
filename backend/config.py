from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

class Config:
    # Database configuration
    DATABASE_PATH = str(Path(__file__).parent / 'data' / 'investment.db')
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ESG_API_TOKEN = os.getenv("ESG_API_TOKEN")
    TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
    TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
    
    # Defaults
    DEFAULT_PERIOD = "1y"
    NEWS_LOOKBACK_DAYS = 30
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'

    # SQLite
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///investment.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False