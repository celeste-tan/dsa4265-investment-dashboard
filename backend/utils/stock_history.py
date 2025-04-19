# === stock_history.py ===
"""
Fetches historical stock data using yfinance, computes technical indicators,
and generates an AI-powered summary using OpenAI. Optionally performs faithfulness evaluation.
"""

# -----------------------------
# Imports
# -----------------------------
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import yfinance as yf
import openai
import pandas_market_calendars as mcal
import os
import re
import json
from flask import request, jsonify

# -----------------------------
# Date Utilities
# -----------------------------
def get_calendar_date_range(period):
    """
    Returns start and end date for the given period using actual NYSE trading calendar.
    Avoids weekends and holidays.
    """
    nyse = mcal.get_calendar("XNYS")
    valid_days = nyse.valid_days(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now()
    )
    end_date = valid_days[-1].to_pydatetime()

    if period == "1d":
        start_date = end_date - timedelta(days=1)
    elif period == "5d":
        start_date = end_date - timedelta(days=7)
    elif period == "1mo":
        start_date = end_date - relativedelta(months=1)
    elif period == "3mo":
        start_date = end_date - relativedelta(months=3)
    elif period == "1y":
        start_date = end_date - relativedelta(years=1)
    elif period == "5y":
        start_date = end_date - relativedelta(years=5)
    elif period == "10y":
        start_date = end_date - relativedelta(years=10)
    elif period == "15y":
        start_date = end_date - relativedelta(years=15)
    else:
        raise ValueError("Invalid period specified")

    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

# -----------------------------
# Historical Data Fetching
# -----------------------------
def fetch_stock_data(ticker_symbol, period, start_date=None, end_date=None):
    """
    Fetches stock data from Yahoo Finance.
    If dates are not provided, they are derived from the period.
    """
    ticker = yf.Ticker(ticker_symbol)

    if period == "1d":
        return ticker.history(period="1d", interval="1m")

    if not start_date or not end_date:
        start_date, end_date = get_calendar_date_range(period)

    return ticker.history(start=start_date, end=end_date)

# -----------------------------
# Technical Indicator Calculations
# -----------------------------
def calculate_sma(data, window):
    return data['Close'].rolling(window=window).mean()

def calculate_ema(data, window):
    return data['Close'].ewm(span=window, adjust=False).mean()

def calculate_volatility(data):
    data['Daily_Return'] = data['Close'].pct_change()
    return data['Daily_Return'].std() * (252 ** 0.5)

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs)).iloc[-1]

# -----------------------------
# Technical Summary Builder
# -----------------------------
def stock_data_summary(data, sma_50, sma_200, ema_50, ema_200, rsi, volatility):
    """
    Builds a textual summary of computed indicators.
    """
    try:
        end_price = data['Close'].iloc[-1]
        return (
            f"Price: {end_price:.2f}%, Volatility: {volatility:.2f}. "
            f"50-day SMA: {sma_50:.2f}, 200-day SMA: {sma_200:.2f}, "
            f"EMA-50: {ema_50:.2f}, EMA-200: {ema_200:.2f}, "
            f"RSI: {rsi:.2f}."
        )
    except Exception as e:
        return f"Error generating summary: {e}"

# -----------------------------
# OpenAI Prompt Constructor
# -----------------------------
def build_stock_prompt(ticker, summary, price, volatility, ma_short, ma_long, ema_short, ema_long, rsi, timeframe):
    """
    Builds a detailed prompt string for OpenAI to generate a beginner-friendly analysis.
    """
    if timeframe == "short-term":
        period = "1-year"
        ma_used = f"SMA(50): {ma_short:.2f}"
        ema_used = f"EMA(50): {ema_short:.2f}"
        ma_label = "50-day"
    else:
        period = "15-year"
        ma_used = f"SMA(200): {ma_long:.2f}"
        ema_used = f"EMA(200): {ema_long:.2f}"
        ma_label = "200-day"

    return (
        f"\U0001F4A1 **Stock Performance**\n\n"
        f"Write a concise stock commentary for **{ticker}**, using the following technical indicators derived from "
        f"{period} historical data:\n\n"
        f"- Current price\n"
        f"- Volatility (annualised standard deviation of daily returns)\n"
        f"- {ma_label} Simple Moving Average (SMA)\n"
        f"- {ma_label} Exponential Moving Average (EMA)\n"
        f"- Relative Strength Index (RSI: 14-day)\n\n"
        f"Return your response in bullet points. Each bullet should explain one of the indicators in clear, beginner-friendly language. "
        f"Do not provide a final recommendation.\n\n"
        f"_Note: All indicators are based on {period} data._\n\n"
        f"Here is the technical data:\n"
        f"1. Current Price: ${price:.2f}\n"
        f"2. Volatility: {volatility:.2f}\n"
        f"3. {ma_used}\n"
        f"4. {ema_used}\n"
        f"5. RSI(14): {rsi:.2f}"
    )

# -----------------------------
# Main Recommendation Generator
# -----------------------------
def get_stock_recommendation(ticker, timeframe, openai_api_key, evaluate=False):
    """
    Retrieves stock data, computes technical indicators with appropriate windows,
    generates GPT-based stock commentary, and optionally performs a faithfulness evaluation.
    """
    period = {"short-term": "1y", "long-term": "15y"}.get(timeframe, timeframe)
    data = fetch_stock_data(ticker, period)
    if data.empty:
        return "No stock data available.", ""

    sma_short = 20 if timeframe == "short-term" else 50
    sma_long = 50 if timeframe == "short-term" else 200
    ema_short = 20 if timeframe == "short-term" else 50
    ema_long = 50 if timeframe == "short-term" else 200
    rsi_window = 10 if timeframe == "short-term" else 14

    price = data['Close'].iloc[-1]
    volatility = calculate_volatility(data)
    ma_50 = calculate_sma(data, sma_short).iloc[-1]
    ma_200 = calculate_sma(data, sma_long).iloc[-1]
    ema_50 = calculate_ema(data, ema_short).iloc[-1]
    ema_200 = calculate_ema(data, ema_long).iloc[-1]
    rsi = calculate_rsi(data, rsi_window)

    summary = stock_data_summary(data, ma_50, ma_200, ema_50, ema_200, rsi, volatility)
    prompt = build_stock_prompt(ticker, summary, price, volatility, ma_50, ma_200, ema_50, ema_200, rsi, timeframe)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        generated_commentary = response.choices[0].message.content.strip()

        # -----------------------------
        # Faithfulness Evaluation (Optional)
        # -----------------------------
        if evaluate and not summary.startswith("Error"):
            evaluation_prompt = (
                f"Evaluate the faithfulness of the following generated commentary based on the provided reference stock metrics. "
                f"Faithfulness means how accurate and grounded the commentary is in the actual data. "
                f"Score it from 0 to 1 (1 being perfectly faithful), and provide a brief explanation.\n\n"
                f"Reference Stock Metrics: \n{summary}\n\n"
                f"Generated Commentary:\n{generated_commentary}"
            )

            try:
                openai.api_key = openai_api_key
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a critical financial stocks metrics fact-checker assessing accuracy of stock recommendation based on these metrics."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature=0.3
                )
                evaluation_result = response.choices[0].message.content.strip()

                score_match = re.search(r"Score\s*[:\-]?\s*([0-1](?:\.\d+)?)", evaluation_result)
                score = float(score_match.group(1)) if score_match else None

                explanation = re.sub(r"Score\s*[:\-]?\s*[0-1](?:\.\d+)?\s*", "", evaluation_result, count=1, flags=re.IGNORECASE).strip()
                if explanation.lower().startswith("explanation:"):
                    explanation = explanation[len("explanation:"):].strip()

                results = {
                    "Ticker": ticker,
                    "Generated Analysis": generated_commentary,
                    "Reference Stock Data": summary,
                    "Faithfulness Evaluation": {
                        "Score": score,
                        "Explanation": explanation
                    }
                }

                output_dir = os.path.join(os.path.dirname(__file__), "..", "faithfulness_eval", "openai_gpt4o_mini")
                os.makedirs(output_dir, exist_ok=True)

                filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{ticker}_stock_history_eval.json"
                with open(os.path.join(output_dir, filename), "w") as f:
                    json.dump(results, f, indent=4)

            except Exception as e:
                print(f"Error evaluating faithfulness: {e}")

        return generated_commentary, summary

    except Exception as e:
        return f"Error calling GenAI API: {e}", summary

# -----------------------------
# Optional Local Test Execution
# -----------------------------
# if __name__ == "__main__":
#     from dotenv import load_dotenv
#     load_dotenv()
#     openai_api_key = os.getenv("OPENAI_API_KEY")
#     result = get_stock_recommendation("PLTR", "long-term", openai_api_key)
#     print(json.dumps(result, indent=2))
