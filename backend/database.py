from extensions import db
from models import FinancialMetric, NewsArticle
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class InvestmentDB:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with application"""
        with app.app_context():
            db.create_all()
            logger.info("Database tables created")

    def get_latest_financial_metric_date(self, ticker):
        """Get the most recent date for financial metrics"""
        result = db.session.query(
            db.func.max(FinancialMetric.date)
        ).filter_by(ticker=ticker).scalar()
        return result

    def get_news_articles(self, ticker, days=30, limit=20):
        """Get cached news articles"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        articles = NewsArticle.query.filter(
            NewsArticle.ticker == ticker,
            NewsArticle.published_date >= cutoff_date
        ).order_by(
            NewsArticle.published_date.desc()
        ).limit(limit).all()
        
        return [{
            'title': a.title,
            'source': a.source,
            'url': a.url,
            'published_date': a.published_date.strftime('%Y-%m-%d'),
            'content': a.content,
            'sentiment_score': a.sentiment_score
        } for a in articles]

    def insert_news_article(self, ticker, title, source, url, published_date, content, sentiment_score=None):
        """Insert news article into database"""
        try:
            article = NewsArticle(
                ticker=ticker,
                title=title,
                source=source,
                url=url,
                published_date=datetime.strptime(published_date, '%Y-%m-%d').date(),
                content=content,
                sentiment_score=sentiment_score
            )
            db.session.add(article)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error inserting news article: {str(e)}")
            return False

    def insert_financial_metric(self, ticker, date, **metrics):
        """Insert financial metrics into database"""
        try:
            metric = FinancialMetric(
                ticker=ticker,
                date=datetime.strptime(date, '%Y-%m-%d').date(),
                **metrics
            )
            db.session.add(metric)
            db.session.commit()
            logger.info(f"Inserted financial metrics for {ticker}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error inserting financial metrics: {str(e)}")
            return False