# from asyncio.log import logger
# import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

import logging
from asyncio.log import logger as asyncio_logger  # Explicit rename

# Your logger (now safe from overwriting)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Use asyncio's logger separately (if needed)
asyncio_logger.warning("This comes from asyncio")


from flask import Flask, request, jsonify
from flask_cors import CORS

from config import Config
from database import db
from utils import (
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
from utils.stock_history import get_stock_recommendation, fetch_stock_data, get_date_range
import openai
import asyncio
from utils.media_sentiment_analysis import get_stock_summary
from utils.financial_summary import (
    get_full_quarterly_data,
    generate_financial_summary,
    generate_ai_investment_commentary,
    filter_financial_data_by_period 
)
from utils.media_sentiment_analysis import initialise_telegram_client

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# ==================== HEALTH ENDPOINT ====================
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

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
        # if latest_date and (datetime.now() - datetime.strptime(latest_date, '%Y-%m-%d')).days < 7:
        #     metrics = db.get_financial_metrics(ticker)
        #     logger.info(f"Cached ESG scores: {metrics}")
        #     return jsonify({
        #         "esg_scores": {
        #             "Total": metrics.get("esg_risk_score", "N/A"),
        #             "Environmental": metrics.get("environmental_score", "N/A"),
        #             "Social": metrics.get("social_score", "N/A"),
        #             "Governance": metrics.get("governance_score", "N/A"),
        #             "Controversy": {
        #                 "Value": metrics.get("controversy_value", "N/A"),
        #                 "Description": metrics.get("controversy_description", "N/A")
        #             }
        #         }
        #     }), 200

        # Fetch ESG data for the ticker
        esg_data = fetch_esg_data(ticker)
    
        if "error" in esg_data:
            return jsonify({"error": esg_data["error"]}), 400
        
        # Store in database
        db.insert_financial_metric(
            ticker=ticker,
            date=datetime.now().strftime('%Y-%m-%d'),
            total_esg_risk_score=esg_data.get('Total ESG Risk Score', 'N/A'),
            environmental_score=esg_data.get('Environmental Risk Score', 'N/A'),
            social_score=esg_data.get('Social Risk Score', 'N/A'),
            governance_score=esg_data.get('Governance Risk Score', 'N/A'),
            controversy_level=esg_data.get('Controversy Level', 'N/A'),
            peer_controversy_min=esg_data.get('Peer Controversy Min', 'N/A'),
            peer_controversy_avg=esg_data.get('Peer Controversy Avg', 'N/A'),
            peer_controversy_max=esg_data.get('Peer Controversy Max', 'N/A')
        )
        return jsonify({"esg_scores": esg_data}), 200
    
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
    esg_response, status_code = get_esg_scores()
    if status_code != 200:
        return esg_response, status_code
    
    esg_data = esg_response.get_json()["esg_scores"]
    
    # Generate AI report
    report = esg_analysis.generate_esg_assessment(
        esg_data,
        app.config['OPENAI_API_KEY']
    )
    
    return jsonify({"report": report}), 200

# ==================== STOCK ENDPOINTS ====================

@app.route("/api/stock-chart", methods=["POST"])
def stock_chart():
    data = request.json
    ticker = data.get("ticker")
    period = data.get("period", app.config['DEFAULT_PERIOD'])

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        # --- 1D special handling ---
        if period == "1d":
            df = stock_history.fetch_stock_data(ticker, "1d")
            prices = []
            for index, row in df.iterrows():
                formatted_time = index.strftime('%H:%M')  # minute granularity
                prices.append({
                    "date": formatted_time,
                    "close": round(row["Close"], 2)
                })
            return jsonify({"prices": prices})

        # === Regular DB storage for other periods ===
        db_start_date = db.get_earliest_price_date(ticker)
        db_end_date = db.get_latest_price_date(ticker)

        if not db_start_date or not db_end_date:
            start_date = "2009-10-03"
        else:
            start_date = (datetime.strptime(db_end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        end_date = datetime.now().strftime("%Y-%m-%d")

        if start_date <= end_date:
            df = stock_history.fetch_stock_data(ticker, "15y", start_date, end_date)
            for index, row in df.iterrows():
                db.insert_stock_price(
                    ticker=ticker,
                    date=index.strftime('%Y-%m-%d'),
                    open_price=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=row["Volume"]
                )

        # Cut period using calendar-based logic
        period_map = {
            "5d": 7, "1mo": 30, "3mo": 90, "1y": 365,
            "5y": 365 * 5, "10y": 365 * 10, "15y": 365 * 15
        }

        num_days = period_map.get(period, 365)
        start_cutoff = (datetime.now() - timedelta(days=num_days * 1.5)).strftime("%Y-%m-%d")
        raw_prices = db.get_stock_prices(ticker, start_date=start_cutoff)

        prices = []
        for p in raw_prices:
            formatted_date = p["date"]
            prices.append({
                "date": formatted_date,
                "close": round(p["close"], 2)
            })

        return jsonify({"prices": prices})

    except Exception as e:
        logger.error(f"Stock chart error: {str(e)}")
        return jsonify({
            "error": "Failed to get stock data",
            "details": str(e) if app.config['DEBUG'] else None
        }), 500

@app.route("/api/stock-history", methods=["POST"])
def get_stock_history():
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
    from utils import media_sentiment_analysis  # delayed import to avoid circular dependency

    data = request.json
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400

    try:
        try:
            summary = asyncio.run(
                media_sentiment_analysis.get_stock_summary(
                    ticker,
                    app.config['OPENAI_API_KEY']
                )
            )
            return jsonify({"summary": summary})
        except Exception as scrape_err:
            logger.error(f"Failed to scrape and summarize: {scrape_err}")
            return jsonify({"error": "Scraping failed", "details": str(scrape_err)}), 500
    except Exception as e:
        logger.error(f"Unexpected error in media sentiment endpoint: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

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
