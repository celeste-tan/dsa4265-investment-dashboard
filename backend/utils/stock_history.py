"""
Handles historical stock data retrieval, computes technical indicators (SMA, EMA, RSI, volatility),
and generates natural language recommendations via OpenAI.
"""

from datetime import datetime, timedelta
import yfinance as yf
import openai
import pandas_market_calendars as mcal
import os
import re
import json

# -----------------------------
# Date Utilities
# -----------------------------

def get_latest_trading_day():
    nyse = mcal.get_calendar('NYSE')
    now = datetime.now()
    schedule = nyse.schedule(start_date=now - timedelta(days=7), end_date=now)
    if schedule.empty:
        raise ValueError("No trading days found in the last week.")
    return schedule.index[-1].strftime('%Y-%m-%d')


def get_date_range(period):
    # Get the latest trading day as the end date
    end = get_latest_trading_day()
    end_dt = datetime.strptime(end, '%Y-%m-%d')

    # Period map in calendar days (rough estimate, used to find start date)
    period_map = {
        "1d": 1, "5d": 7, "1mo": 30, "3mo": 90,
        "1y": 365, "5y": 365 * 5, "10y": 365 * 10, "15y": 365 * 15
    }

    if period not in period_map:
        raise ValueError("Invalid period specified")

    # Get rough calendar range
    start_candidate = end_dt - timedelta(days=period_map[period] * 1.5)

    # Filter real trading days between start and end
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=start_candidate, end_date=end_dt)
    if schedule.empty:
        raise ValueError(f"No trading days found between {start_candidate} and {end_dt}.")

    start = schedule.index[0].strftime('%Y-%m-%d')
    return start, end


# -----------------------------
# Fetch Historical Data
# -----------------------------
def fetch_stock_data(ticker_symbol, period, start_date=None, end_date=None):
    ticker = yf.Ticker(ticker_symbol)
    
    # For 1-day, request 1-minute interval explicitly
    if period == "1d":
        return ticker.history(period="1d", interval="1m")

    # For everything else, use standard daily data
    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)
    return ticker.history(start=start_date, end=end_date)

# -----------------------------
# Technical Indicators
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
# Summary Generator
# -----------------------------
def stock_data_summary(data, sma_50, sma_200, ema_50, ema_200, rsi, volatility):
    """Generate a human-readable summary based on the calculated indicators."""
    try:
        start_price = data['Close'].iloc[0]
        end_price = data['Close'].iloc[-1]
        pct_change = ((end_price - start_price) / start_price) * 100
        summary = (
            f"Price change: {pct_change:.2f}%. Volatility: {volatility:.2f}. "
            f"50-day SMA: {sma_50:.2f}, 200-day SMA: {sma_200:.2f}, "
            f"EMA-50: {ema_50:.2f}, EMA-200: {ema_200:.2f}, "
            f"RSI: {rsi:.2f}."
        )
        return summary
    except Exception as e:
        return f"Error generating summary: {e}"


# -----------------------------
# Prompt Builder
# -----------------------------
def build_stock_prompt(ticker, summary, price, volatility, ma_short, ma_long, ema_short, ema_long, rsi, timeframe):
    """
    Construct prompt to request a technical commentary from OpenAI.
    Includes only relevant SMA/EMA depending on short-term (50-day) or long-term (200-day) strategy.
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
        f"💡 **Stock Performance**\n\n"
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
# Main Recommendation Function
# -----------------------------
def get_stock_recommendation(ticker, timeframe, openai_api_key, evaluate=False):
    """
    Retrieves stock data, computes technical indicators with appropriate windows based on timeframe,
    and generates GPT-based bullet-point commentary.
    """
    period = {"short-term": "1y", "long-term": "15y"}.get(timeframe, timeframe)
    data = fetch_stock_data(ticker, period)
    if data.empty:
        return "No stock data available.", ""

    # Adjust indicator windows based on time horizon
    sma_short = 20 if timeframe == "short-term" else 50
    sma_long = 50 if timeframe == "short-term" else 200
    ema_short = 20 if timeframe == "short-term" else 50
    ema_long = 50 if timeframe == "short-term" else 200
    rsi_window = 10 if timeframe == "short-term" else 14

    # Compute indicators
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

        # Do faithfulness evaluation
        if evaluate and not summary.startswith("Error"):
            """
            Evaluate the faithfulness of stock history commentary for a ticker by comparing them to the source stock data.
            Saves results as a JSON file in the 'faithfulness_eval' folder.
            """

            evaluation_prompt = (
                f"Evaluate the faithfulness of the following generated commentary based on the provided reference stock metrics."
                f"Faithfulness means how accurate and grounded the commentary is in the actual data."
                f"Score it from 0 to 1 (1 bring perfectly faithful), and provide a brief explanation.\n\n"
                f"Reference Stock Metrics: \n{summary}\n\n"
                f"Generated Commentary\n{generated_commentary}"
            )

            try:
                openai.api_key = openai_api_key
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a critical financial stocks metrics fact-checker assesing accuracy of stock recommendation based on these metrics."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature = 0.3
                )
                evaluation_result = response.choices[0].message.content.strip()

                # Try to extract score and explanation
                score_match = re.search(r"Score\s*[:\-]?\s*([0-1](?:\.\d+)?)", evaluation_result)
                score = float(score_match.group(1)) if score_match else None

                explanation = re.sub(r"Score\s*[:\-]?\s*[0-1](?:\.\d+)?\s*", "", evaluation_result, count=1, flags=re.IGNORECASE).strip()
                if explanation.lower().startswith("explanation:"):
                    explanation = explanation[len("explanation:"):].strip()
                
                # Save to JSON
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

                filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{ticker}_stock_history_openai_eval.json"
                filepath = os.path.join(output_dir, filename)

                with open(filepath, "w") as f:
                    json.dump(results, f, indent=4)
                
            except Exception as e:
                print(f"Error evaluating faithfulness: {e}")

        return generated_commentary, summary
    
    except Exception as e:
        return f"Error calling GenAI API: {e}", summary

# -----------------------------------------------------------------------------------------
# Evaluation Testing (Commented out by default, only run when evaluation needs to be done)
# -----------------------------------------------------------------------------------------
# if __name__ == "__main__":
#     openai_api_key = os.getenv("OPENAI_API_KEY")
#     result = get_stock_recommendation("TSLA", "long-term", openai_api_key)
#     print(json.dumps(result, indent=2))
