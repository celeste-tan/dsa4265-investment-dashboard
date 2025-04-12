from extensions import db
from datetime import datetime

class FinancialMetric(db.Model):
    __tablename__ = 'financial_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    esg_risk_score = db.Column(db.Float)
    environmental_score = db.Column(db.Float)
    social_score = db.Column(db.Float)
    governance_score = db.Column(db.Float)
    controversy_value = db.Column(db.String(50))
    controversy_description = db.Column(db.Text)
    
    __table_args__ = (
        db.Index('idx_financial_metrics_ticker_date', 'ticker', 'date'),
    )

class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), unique=True, nullable=False)
    published_date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text)
    sentiment_score = db.Column(db.Float)
    sentiment_label = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.Index('idx_news_ticker_date', 'ticker', 'published_date'),
        db.UniqueConstraint('ticker', 'url', name='uq_news_ticker_url')
    )