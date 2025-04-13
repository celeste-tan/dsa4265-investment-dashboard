import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import current_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InvestmentDB:
    def __init__(self, app=None):
        self.db_path = None
        self.conn = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.db_path = app.config['DATABASE_PATH']
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with app.app_context():
            self._initialize_db()

    def _initialize_db(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
        
            # Stock prices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL, high REAL, low REAL, close REAL,
                    volume INTEGER,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, date)
                )
            ''')
        
            # News articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    published_date TEXT NOT NULL,
                    content TEXT,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
            # Financial metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS financial_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    dividend_yield REAL,
                    market_cap REAL,
                    esg_risk_score REAL,
                    environmental_score REAL,
                    social_score REAL,
                    governance_score REAL,
                    controversy_value TEXT,
                    controversy_description TEXT,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, date)
                )
            ''')
        
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_ticker_date ON stock_prices(ticker, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_ticker_date ON news_articles(ticker, published_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_financial_ticker_date ON financial_metrics(ticker, date)')
        
            self.conn.commit()
            logger.info(f"Database initialization completed, conn: {self.conn}")
        
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    # Stock Price Methods
    def insert_stock_price(self, ticker: str, date: str, open_price: float, high: float, 
                         low: float, close: float, volume: int) -> bool:
        try:
            self.conn.execute('''
                INSERT OR REPLACE INTO stock_prices 
                (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ticker, date, open_price, high, low, close, volume))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting stock price: {e}")
            return False

    def get_stock_prices(self, ticker: str, start_date: str = None, end_date: str = None) -> list:
        query = 'SELECT date, open, high, low, close, volume FROM stock_prices WHERE ticker = ?'
        params = [ticker]
        
        if start_date and end_date:
            query += ' AND date BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        elif start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        elif end_date:
            query += ' AND date <= ?'
            params.append(end_date)
            
        query += ' ORDER BY date ASC'
        
        try:
            cursor = self.conn.execute(query, params)
            return [dict(zip(['date', 'open', 'high', 'low', 'close', 'volume'], row)) 
                    for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching stock prices: {e}")
            return []
        except Exception as e:
            logger.error(f"Exception: {e}, conn: {self.conn}")
            return []

    # News Methods
    def insert_news_article(self, ticker: str, title: str, source: str, url: str,
                          published_date: str, content: str, sentiment_score: float = None) -> bool:
        try:
            self.conn.execute('''
                INSERT OR IGNORE INTO news_articles
                (ticker, title, source, url, published_date, content, sentiment_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ticker, title, source, url, published_date, content, sentiment_score))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting news article: {e}")
            return False

    def get_news_articles(self, ticker: str, days: int = 30, limit: int = 10) -> list:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            cursor = self.conn.execute('''
                SELECT title, source, url, published_date, content, sentiment_score
                FROM news_articles
                WHERE ticker = ? AND published_date BETWEEN ? AND ?
                ORDER BY published_date DESC
                LIMIT ?
            ''', (ticker, start_date, end_date, limit))
            
            return [dict(zip(['title', 'source', 'url', 'published_date', 'content', 'sentiment_score'], row))
                    for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching news articles: {e}")
            return []

    # Financial Metrics Methods
    def insert_financial_metric(self, ticker: str, date: str, **metrics) -> bool:
        try:
            self.conn.execute('''
                INSERT OR REPLACE INTO financial_metrics
                (ticker, date, pe_ratio, pb_ratio, dividend_yield, market_cap,
                 esg_risk_score, environmental_score, social_score, governance_score,
                 controversy_value, controversy_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker, date,
                metrics.get('pe_ratio'),
                metrics.get('pb_ratio'),
                metrics.get('dividend_yield'),
                metrics.get('market_cap'),
                metrics.get('esg_risk_score'),
                metrics.get('environmental_score'),
                metrics.get('social_score'),
                metrics.get('governance_score'),
                metrics.get('controversy_value'),
                metrics.get('controversy_description')
            ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting financial metric: {e}")
            return False

    def get_financial_metrics(self, ticker: str) -> dict:
        try:
            cursor = self.conn.execute('''
                SELECT * FROM financial_metrics
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT 1
            ''', (ticker,))
            
            row = cursor.fetchone()
            if not row:
                return {}
                
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
        except sqlite3.Error as e:
            logger.error(f"Error fetching financial metrics: {e}")
            return {}

    def get_latest_financial_metric_date(self, ticker: str) -> str:
        try:
            cursor = self.conn.execute('''
                SELECT MAX(date) FROM financial_metrics WHERE ticker = ?
            ''', (ticker,))
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting latest financial date: {e}")
            return None
    def get_earliest_price_date(self, ticker: str) -> str:
        """Return the earliest date for which stock price is stored for a given ticker."""
        try:
            cursor = self.conn.execute(
                '''SELECT MIN(date) FROM stock_prices WHERE ticker = ?''',
                (ticker,)
            )
            result = cursor.fetchone()[0]
            return result if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting earliest price date for {ticker}: {e}")
            return None

    def get_latest_price_date(self, ticker: str) -> str:
        """Return the latest date for which stock price is stored for a given ticker."""
        try:
            cursor = self.conn.execute(
                '''SELECT MAX(date) FROM stock_prices WHERE ticker = ?''',
                (ticker,)
            )
            result = cursor.fetchone()[0]
            return result if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting latest price date for {ticker}: {e}")
            return None

    def close(self, exception=None):
        if self.conn:
            self.conn.close()
            self.conn = None

db = InvestmentDB()
