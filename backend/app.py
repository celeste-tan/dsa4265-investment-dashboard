import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from asyncio.log import logger
from flask import Flask, request, jsonify
from flask_cors import CORS

from .config import Config
from .database import db
from .utils import (
    esg_analysis,
    stock_history,
    media_sentiment_analysis,
    financial_summary,
    holistic_summary
)
from datetime import datetime, timedelta
import os
from utils.holistic_summary import get_holistic_recommendation
from utils.esg_analysis import get_esg_report, fetch_esg_data
from config import DEFAULT_PERIOD, OPENAI_API_KEY, ESG_API_TOKEN
from utils.stock_history import get_stock_recommendation, fetch_stock_data
import openai
import asyncio
from utils.media_sentiment_analysis import get_stock_summary
from utils.financial_summary import (
    get_full_quarterly_data,
    generate_financial_summary,
    generate_ai_investment_commentary,
    filter_financial_data_by_period 
)
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# ==================== ESG ENDPOINTS ====================

@app.route("/api/esg-scores", methods=["POST"])
def get_esg_scores():
    """Endpoint 1: Get raw ESG scores with database caching"""
    data = request.json
    ticker = data.get("ticker", "").upper()

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400
    
    try:
        # Check cache first (valid for 7 days)
        latest_date = db.get_latest_financial_metric_date(ticker)
        if latest_date and (datetime.now() - datetime.strptime(latest_date, '%Y-%m-%d')).days < 7:
            metrics = db.get_financial_metrics(ticker)
            return jsonify({
                "esg_scores": {
                    "Total": metrics.get("esg_risk_score"),
                    "Environmental": metrics.get("environmental_score"),
                    "Social": metrics.get("social_score"),
                    "Governance": metrics.get("governance_score"),
                    "Controversy": {
                        "Value": metrics.get("controversy_value", "N/A"),
                        "Description": metrics.get("controversy_description", "N/A")
                    }
                }
            })

        # Fetch ESG data for the ticker
        esg_data = fetch_esg_data(ticker)
    
        if "error" in esg_data:
            return jsonify({"error": esg_data["error"]}), 400
        
        # Store in database
        db.insert_financial_metric(
            ticker=ticker,
            date=datetime.now().strftime('%Y-%m-%d'),
            esg_risk_score=esg_data.get("Total"),
            environmental_score=esg_data.get("Environmental"),
            social_score=esg_data.get("Social"),
            governance_score=esg_data.get("Governance"),
            controversy_value=esg_data.get("Controversy", {}).get("Value"),
            controversy_description=esg_data.get("Controversy", {}).get("Description")
        )
        
        return jsonify({"esg_scores": esg_data})
    
    except Exception as e:
        logger.error(f"ESG scores error: {str(e)}")
        return jsonify({
            "error": "Failed to get ESG scores",
            "details": str(e) if app.config['DEBUG'] else None
        }), 500

@app.route("/api/esg-gen-report", methods=["POST"])
def generate_esg_report():
    """Endpoint 2: Generate AI analysis of ESG scores"""
    data = request.json
    ticker = data.get("ticker", "").upper()

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    # First get scores (uses cached data if available)
    esg_response = get_esg_scores()
    if esg_response.status_code != 200:
        return esg_response
    
    esg_data = esg_response.get_json()["esg_scores"]
    
    # Generate AI report
    report = esg_analysis.generate_esg_assessment(
        {
            "Stock": ticker,
            "Total ESG Risk Score": esg_data["Total"],
            "Environmental Risk Score": esg_data["Environmental"],
            "Social Risk Score": esg_data["Social"],
            "Governance Risk Score": esg_data["Governance"],
            "Controversy Level": esg_data["Controversy"]
        },
        app.config['OPENAI_API_KEY']
    )
    
    return jsonify({"report": report})

# ==================== STOCK ENDPOINTS ====================

@app.route("/api/stock-chart", methods=["POST"])
def stock_chart():
    """Endpoint 3: Get historical price data with caching"""
    data = request.json
    ticker = data.get("ticker")
    period = data.get("period", app.config['DEFAULT_PERIOD'])

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        # Determine date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        if period == "1d":
            start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif period == "1w":
            start_date = (datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d')
        elif period == "1mo":
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif period == "1y":
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        else:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')  # Default to 1 year

        # Check database cache first
        cached_prices = db.get_stock_prices(ticker, start_date, end_date)
        
        if cached_prices and len(cached_prices) > 10:  # Use cache if sufficient data exists
            prices = [{
                "date": price['date'],
                "close": round(float(price['close']), 2)
            } for price in cached_prices]
        else:
            # Fetch fresh data if cache is insufficient
            df = stock_history.fetch_stock_data(ticker, period)
            prices = []
            for index, row in df.iterrows():
                date_str = index.strftime('%Y-%m-%d')
                prices.append({
                    "date": date_str,
                    "close": round(row["Close"], 2)
                })
                # Store in database
                db.insert_stock_price(
                    ticker=ticker,
                    date=date_str,
                    open_price=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=row["Volume"]
                )
        
        return jsonify({"prices": prices})
    except Exception as e:
        logger.error(f"Stock chart error: {str(e)}")
        return jsonify({
            "error": "Failed to get stock data",
            "details": str(e) if app.config['DEBUG'] else None
        }), 500

@app.route("/api/stock-history", methods=["POST"])
def get_stock_recommendation():
    """Endpoint 4: Get AI-generated stock recommendation"""
    data = request.json
    ticker = data.get("ticker")
    timeframe = data.get("timeframe", "short-term")

    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400

    recommendation, _ = get_stock_recommendation(ticker, timeframe, os.getenv("OPENAI_API_KEY", ""))
    return jsonify({"recommendation": recommendation})
# Finanical Summary
# 1 Chart Data
@app.route("/api/financial-chart", methods=["POST"])
def financial_chart():
    data = request.json
    ticker = data.get("ticker", "").upper()
    period = data.get("period", "1y")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    try:
        df_all = get_full_quarterly_data(ticker)
        df = filter_financial_data_by_period(df_all, period)

        # Drop rows with any NaN values to avoid frontend issues
        print("✅ Original rows:", len(df))
        df = df.dropna()
        print("🧹 Cleaned rows:", len(df))


        chart_data = []
        for _, row in df.iterrows():
            chart_data.append({
                "quarter": row["Quarter"],
                "revenue": row["Revenue"],
                "net_income": row["Net Income"],
                "free_cash_flow": row["Free Cash Flow"]
            })

        return jsonify({"data": chart_data})
    except Exception as e:
        logger.error(f"Financial chart error for {ticker}: {str(e)}")
        return jsonify({
            "error": "Failed to get financial data",
            "details": str(e) if app.config['DEBUG'] else None
        }), 500


# 2️Summary & Commentary
@app.route("/api/financial-recommendation", methods=["POST"])
def financial_recommendation():
    data = request.json
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    try:
        df = get_full_quarterly_data(ticker)
        summary = generate_financial_summary(df, ticker)
        commentary = generate_ai_investment_commentary(summary, os.getenv("OPENAI_API_KEY"))
        return jsonify({
            "summary": summary,
            "commentary": commentary
        })
    except Exception as e:
        logger.error(f"Financial recommendation failed for {ticker}: {str(e)}")
        return jsonify({
            "error": "Failed to generate financial analysis",
            "details": str(e) if app.config['DEBUG'] else None
        }), 500

# ==================== MEDIA SENTIMENT ENDPOINT ====================

@app.route("/api/media-sentiment-summary", methods=["POST"])
def get_media_sentiment():
    """Endpoint 5: Get news sentiment analysis with caching"""
    data = request.json
    ticker = data.get("ticker", "").upper()

    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400

    try:
        # Check for cached news (last 30 days)
        news_articles = db.get_news_articles(ticker, days=app.config['NEWS_LOOKBACK_DAYS'])
        
        if not news_articles:
            # Scrape fresh news if none in cache
            try:
                news_articles = asyncio.run(
                    media_sentiment_analysis.scrape_telegram_headlines()
                )
            except Exception as scrape_error:
                logger.error(f"Failed to scrape Telegram headlines: {str(scrape_error)}")
                return jsonify({
                    "error": "Failed to fetch news articles",
                    "details": str(scrape_error)
                }), 500

            # Store new articles with individual error handling
            successful_inserts = 0
            for article in news_articles:
                try:
                    db.insert_news_article(
                        ticker=ticker,
                        title=article.get('title'),
                        source="Telegram",
                        url=article.get('url'),
                        published_date=article.get('date'),
                        content=article.get('content'),
                        sentiment_score=None
                    )
                    successful_inserts += 1
                except Exception as insert_error:
                    logger.error(f"Failed to insert article {article.get('url')}: {str(insert_error)}")
                    continue
            
            if successful_inserts == 0:
                return jsonify({
                    "error": "Failed to store any news articles",
                    "details": "Database insertion failed for all articles"
                }), 500

        # Generate summary
        try:
            summary = asyncio.run(
                media_sentiment_analysis.get_stock_summary(
                    ticker,
                    app.config['OPENAI_API_KEY']
                )
            )
            return jsonify({"summary": summary})
            
        except Exception as analysis_error:
            logger.error(f"Sentiment analysis failed: {str(analysis_error)}")
            return jsonify({
                "error": "Failed to generate sentiment analysis",
                "details": str(analysis_error)
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in media sentiment endpoint: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": "An unexpected error occurred"
        }), 500
    
# At A Glance Holistic Summary
@app.route("/api/holistic-summary", methods=["POST"])
def holistic_summary():
    data = request.json
    ticker = data.get("ticker", "").upper()
    timeframe = data.get("timeframe", "short-term")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    try:
        summary = asyncio.run(get_holistic_recommendation(ticker, timeframe))
        return jsonify({"summary": summary})
    except Exception as e:
        logger.error(f"Holistic summary failed for {ticker}: {str(e)}")
        return jsonify({
            "error": "Failed to generate holistic analysis",
            "details": str(e) if app.config['DEBUG'] else None
        }), 500


if __name__ == "__main__":
    app.run(debug=True)