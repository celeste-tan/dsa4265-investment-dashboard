from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os

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

# ESG ANALYSIS
@app.route("/api/esg-scores", methods=["POST"])
def get_esg_scores():
    """New route that returns only the individual ESG scores."""
    data = request.json
    ticker = data.get("ticker", "").upper()
    print(f"Received ticker: {ticker}")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    # Fetch ESG data for the ticker
    esg_data = fetch_esg_data(ticker)
    
    if "error" in esg_data:
        return jsonify({"error": esg_data["error"]}), 400

    print(f"Extracted ESG Scores: {esg_data}")
    
    return jsonify({"esg_scores": esg_data})

@app.route("/api/esg-gen-report", methods=["POST"])
def get_esg():
    data = request.json
    ticker = data.get("ticker", "").upper()
    print(f"Received ticker: {ticker}")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    report = get_esg_report(ticker, OPENAI_API_KEY)
    print(f"Generated ESG Report: {report}")
    return jsonify({"report": report})


# MEDIA SENTIMENT ANALYSIS
@app.route("/api/media-sentiment-summary", methods=["POST"])
def get_media_summary():
    data = request.json
    ticker = data.get("ticker", "").upper()
    print(f"Received ticker: {ticker}")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400
    
    summary = asyncio.run(get_stock_summary(ticker, OPENAI_API_KEY))
    print(summary)
    return jsonify({"summary": summary})

# STOCK HISTORY PERFORMANCE
@app.route("/api/stock-chart", methods=["POST"])
def stock_chart():
    data = request.json
    ticker = data.get("ticker")
    period = data.get("period", "1y")

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        df = fetch_stock_data(ticker, period)
        prices = []
        for index, row in df.iterrows():
            prices.append({
                "date": index.strftime("%Y-%m-%d"),
                "close": round(row["Close"], 2)
            })
        return jsonify({"prices": prices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock-history", methods=["POST"])
def stock_history():
    import os

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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
