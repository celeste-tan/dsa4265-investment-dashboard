# === database.py ===
"""
SQLite3-backed local database for storing and retrieving Telegram headlines.
Used to cache news data and reduce repeated scraping.
"""

# -----------------------------
# Imports
# -----------------------------
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# -----------------------------
# Logger Setup
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Database Wrapper Class
# -----------------------------
class InvestmentDB:
    """
    Lightweight SQLite3 database manager for storing ticker-specific headlines.
    """

    def __init__(self, app=None):
        self.db_path = None
        self.conn = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Called by Flask to load the database configuration and initialize schema.
        """
        self.db_path = app.config['DATABASE_PATH']
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with app.app_context():
            self._initialize_db()

    def _initialize_db(self):
        """
        Creates the headlines table if it doesn't exist.
        """
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS headlines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date DATETIME NOT NULL,
                    message TEXT NOT NULL,
                    UNIQUE(ticker, date, message)
                )
            ''')
            self.conn.commit()
            logger.info("Headlines table initialized.")
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def get_headlines(self, ticker: str, after: datetime) -> list:
        """
        Retrieves headlines for a given ticker newer than the provided datetime.
        """
        try:
            cursor = self.conn.execute('''
                SELECT date, message
                FROM headlines
                WHERE ticker = ? AND date > ?
                ORDER BY date ASC
            ''', (ticker, after))
            return [dict(zip(['date', 'message'], row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching headlines: {e}")
            return []

    def save_headlines(self, ticker: str, headlines: list) -> None:
        """
        Inserts a list of headlines into the database, avoiding duplicates.
        """
        try:
            for headline in headlines:
                self.conn.execute('''
                    INSERT OR IGNORE INTO headlines
                    (ticker, date, message)
                    VALUES (?, ?, ?)
                ''', (ticker, headline['date'], headline['message']))
            self.conn.commit()
            logger.info(f"{len(headlines)} headlines saved for {ticker}")
        except sqlite3.Error as e:
            logger.error(f"Error saving headlines: {e}")

    def close(self, exception=None):
        """
        Cleanly closes the database connection.
        """
        if self.conn:
            self.conn.close()
            self.conn = None

# -----------------------------
# Singleton Export
# -----------------------------
db = InvestmentDB()
