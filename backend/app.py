# === app.py ===
"""
Main Flask backend application that handles ESG, stock history, financials,
media sentiment, and holistic recommendation endpoints.
"""

# -----------------------------
# Imports
# -----------------------------
import os
import logging
import asyncio
from datetime import datetime, timedelta

import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Internal modules
from config import Config
from database import db
from utils.esg_analysis import fetch_esg_data, generate_esg_assessment
from utils.stock_history import get_stock_recommendation, fetch_stock_data, get_calendar_date_range
from utils.financial_summary import (
    get_full_quarterly_data,
    get_full_annual_data,
    generate_financial_summary,
    generate_ai_investment_commentary,
)
from utils.media_analysis import get_stock_summary
from utils.holistic_summary import get_holistic_recommendation

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
db.init_app(app)
OPENAI_API_KEY = app.config['OPENAI_API_KEY']

# -----------------------------
# Health Check
# -----------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    """Simple GET endpoint to check if the API is running."""
    return jsonify({"status": "ok"}), 200

# -----------------------------
# ESG Endpoints
# -----------------------------
@app.route("/api/esg-scores", methods=["POST"])
def get_esg_scores():
    """Fetch ESG scores from yfinance."""
    data = request.json
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400
    try:
        esg_data = fetch_esg_data(ticker)
        if "error" in esg_data:
            return jsonify({"error": esg_data["error"]}), 400
        return jsonify({"esg_scores": esg_data}), 200
    except Exception as e:
        logger.error(f"ESG scores error: {str(e)}")
        return jsonify({"error": "Failed to get ESG scores", "details": str(e) if app.config['DEBUG'] else None}), 500

@app.route("/api/esg-gen-report", methods=["POST"])
def generate_esg_report():
    """Generate ESG report using GPT."""
    data = request.json
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400
    esg_response, status_code = get_esg_scores()
    if status_code != 200:
        return esg_response, status_code
    esg_data = esg_response.get_json().get("esg_scores", {})
    report = generate_esg_assessment(esg_data, OPENAI_API_KEY)
    return jsonify({"report": report}), 200

# -----------------------------
# Stock History & Chart Endpoints
# -----------------------------
@app.route("/api/stock-chart", methods=["POST"])
def stock_chart():
    """Fetch and return historical stock prices for charting."""
    data = request.json
    ticker = data.get("ticker")
    period = data.get("period", app.config['DEFAULT_PERIOD'])

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        if period == "1d":
            df = fetch_stock_data(ticker, "1d")
            prices = [
                {"date": index.strftime('%H:%M'), "close": round(row["Close"], 2)}
                for index, row in df.iterrows()
            ]
            return jsonify({"prices": prices})

        start_date, end_date = get_calendar_date_range(period)
        df = fetch_stock_data(ticker, period, start_date, end_date)
        prices = [
            {"date": index.strftime('%Y-%m-%d'), "close": round(row["Close"], 2)}
            for index, row in df.iterrows()
        ]
        return jsonify({"prices": prices})

    except Exception as e:
        logger.error(f"Stock chart error: {str(e)}")
        return jsonify({"error": "Failed to get stock data", "details": str(e) if app.config['DEBUG'] else None}), 500

@app.route("/api/stock-history", methods=["POST"])
def get_stock_history():
    """Get technical commentary from OpenAI based on historical stock data."""
    data = request.json
    ticker = data.get("ticker")
    timeframe = data.get("timeframe", "short-term")
    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400
    recommendation, _ = get_stock_recommendation(ticker, timeframe, OPENAI_API_KEY)
    return jsonify({"recommendation": recommendation})

# -----------------------------
# Financial Data Endpoints
# -----------------------------
@app.route("/api/financial-chart", methods=["POST"])
def get_financial_chart():
    """Returns financial chart data (quarterly/annual) for a given stock."""
    data = request.get_json()
    ticker = data.get('ticker')
    period = data.get('period', '5y')
    try:
        if period in ['5y', '10y', '15y']:
            df = get_full_annual_data(ticker)
            label_key = "Year"
        else:
            df = get_full_quarterly_data(ticker)
            label_key = "Quarter"

        chart_data = [
            {
                "label": row[label_key],
                "revenue": row["Revenue"],
                "net_income": row["Net Income"],
                "free_cash_flow": row["Free Cash Flow"]
            }
            for _, row in df.iterrows()
        ]
        return jsonify({"data": chart_data})
    except Exception as e:
        logger.error(f"Financial chart error: {str(e)}")
        return jsonify({"error": "Failed to get financial data", "details": str(e) if app.config['DEBUG'] else None}), 500

@app.route("/api/financial-recommendation", methods=["POST"])
def financial_recommendation():
    """Returns AI-generated investment commentary from financial metrics."""
    data = request.json
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400
    try:
        df = get_full_quarterly_data(ticker)
        summary = generate_financial_summary(df, ticker)
        commentary = generate_ai_investment_commentary(summary, OPENAI_API_KEY)
        return jsonify({"summary": summary, "commentary": commentary})
    except Exception as e:
        logger.error(f"Financial recommendation failed for {ticker}: {str(e)}")
        return jsonify({"error": "Failed to generate financial analysis", "details": str(e) if app.config['DEBUG'] else None}), 500

# -----------------------------
# Media Sentiment Endpoint
# -----------------------------
@app.route("/api/media-sentiment-summary", methods=["POST"])
def get_media_sentiment():
    """Returns a short media sentiment summary based on Telegram headlines."""
    data = request.json
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400
    try:
        summary = asyncio.run(get_stock_summary(ticker, OPENAI_API_KEY))
        return jsonify({"summary": summary})
    except Exception as e:
        logger.error(f"Media sentiment error for {ticker}: {str(e)}")
        return jsonify({"error": "Failed to retrieve media sentiment", "details": str(e) if app.config['DEBUG'] else None}), 500

# -----------------------------
# Holistic Investment Recommendation
# -----------------------------
@app.route("/api/holistic-summary", methods=["POST"])
def holistic_summary_endpoint():
    """Returns a multi-dimensional stock summary combining all data signals."""
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
        return jsonify({"error": "Failed to generate holistic analysis", "details": str(e) if app.config['DEBUG'] else None}), 500

# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
