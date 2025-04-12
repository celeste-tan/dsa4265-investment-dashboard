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
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    PHONE = os.getenv("PHONE")
    
    # Defaults
    DEFAULT_PERIOD = "1y"
    DEFAULT_NEWS_DAYS = 30
    NEWS_LOOKBACK_DAYS = 30
