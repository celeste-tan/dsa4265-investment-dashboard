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
import asyncio
from datetime import datetime, timedelta
import os

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

    # Fetch fresh data if not in cache
    esg_data = esg_analysis.fetch_esg_data(ticker, app.config['ESG_API_TOKEN'])
    if "error" in esg_data:
        return jsonify({"error": esg_data["error"]}), 400

    # Store in database
    db.insert_financial_metric(
        ticker=ticker,
        date=datetime.now().strftime('%Y-%m-%d'),
        esg_risk_score=esg_data.get("Total ESG Risk Score"),
        environmental_score=esg_data.get("Environmental Risk Score"),
        social_score=esg_data.get("Social Risk Score"),
        governance_score=esg_data.get("Governance Risk Score"),
        controversy_value=esg_data.get("Controversy Level", {}).get("Value"),
        controversy_description=esg_data.get("Controversy Level", {}).get("Description")
    )
    
    return jsonify({
        "esg_scores": {
            "Total": esg_data.get("Total ESG Risk Score"),
            "Environmental": esg_data.get("Environmental Risk Score"),
            "Social": esg_data.get("Social Risk Score"),
            "Governance": esg_data.get("Governance Risk Score"),
            "Controversy": esg_data.get("Controversy Level", {})
        }
    })

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
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock-history", methods=["POST"])
def get_stock_recommendation():
    """Endpoint 4: Get AI-generated stock recommendation"""
    data = request.json
    ticker = data.get("ticker")
    timeframe = data.get("timeframe", "short-term")

    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400

    try:
        recommendation, technical_summary = stock_history.get_stock_recommendation(
            ticker, 
            timeframe,
            app.config['OPENAI_API_KEY']
        )
        return jsonify({
            "recommendation": recommendation,
            "technical_summary": technical_summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            news_articles = asyncio.run(
                media_sentiment_analysis.scrape_telegram_headlines()
            )
            # Store new articles
            for article in news_articles:
                db.insert_news_article(
                    ticker=ticker,
                    title=article.get('title'),
                    source="Telegram",
                    url=article.get('url'),
                    published_date=article.get('date'),
                    content=article.get('content'),
                    sentiment_score=None  # Will be calculated during analysis
                )

        # Generate summary (using cached or fresh articles)
        summary = asyncio.run(
            media_sentiment_analysis.get_stock_summary(
                ticker,
                app.config['OPENAI_API_KEY']
            )
        )
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== HOLISTIC SUMMARY ENDPOINT ====================

@app.route("/api/holistic-summary", methods=["POST"])
def get_holistic_summary():
    """Endpoint 6: Combined analysis of all factors"""
    data = request.json
    ticker = data.get("ticker", "").upper()
    
    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400

    try:
        # Get all components
        stock_resp = get_stock_recommendation()
        if stock_resp.status_code != 200:
            return stock_resp
        stock_data = stock_resp.get_json()
        
        esg_resp = generate_esg_report()
        if esg_resp.status_code != 200:
            return esg_resp
        esg_report = esg_resp.get_json()["report"]
        
        fin_summary = financial_summary.generate_summary(ticker)
        
        news_resp = get_media_sentiment()
        if news_resp.status_code != 200:
            return news_resp
        news_summary = news_resp.get_json()["summary"]
        
        # Combine into holistic view
        report = holistic_summary.get_holistic_recommendation(
            ticker, 
            stock_data["recommendation"],
            esg_report,
            fin_summary,
            news_summary
        )
        
        return jsonify({"report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)