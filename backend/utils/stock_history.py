# === stock_history.py ===
"""
Handles historical stock data retrieval, computes technical indicators (SMA, EMA, RSI, volatility),
and generates natural language recommendations via OpenAI.
"""
from datetime import datetime
from pandas.tseries.offsets import BDay
import yfinance as yf
import openai

# -----------------------------
# Stock Data Functions
# -----------------------------
def get_date_range(period):
    """Return the start and end dates for a given period using trading days."""
    today = datetime.today()
    period_map = {
        "1d": 1, "5d": 5, "1mo": 21, "3mo": 63,
        "1y": 252, "5y": 252*5, "10y": 252*10, "15y": 252*15
    }
    if period not in period_map:
        raise ValueError("Invalid period specified")
    start = today - BDay(period_map[period])
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

def fetch_stock_data(ticker_symbol, period, start_date=None, end_date=None):
    """Fetch historical stock data for a given ticker and period."""
    ticker = yf.Ticker(ticker_symbol)
    if period == "1d":
        return ticker.history(period="1d", interval="1m")
    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)
    return ticker.history(start=start_date, end=end_date)

# -----------------------------
# Technical Indicators
# -----------------------------
def calculate_sma(data, window=50):
    return data['Close'].rolling(window=window).mean()

def calculate_ema(data, window=50):
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

def stock_data_summary(data):
    """Generate a textual summary based on technical indicators."""
    if data.empty:
        return "No data available to summarize."
    try:
        start_price = data['Close'].iloc[0]
        end_price = data['Close'].iloc[-1]
        pct_change = ((end_price - start_price) / start_price) * 100
        summary = (
            f"Price change: {pct_change:.2f}%. Volatility: {calculate_volatility(data):.2f}. "
            f"50-day SMA: {calculate_sma(data, 50).iloc[-1]:.2f}, 200-day SMA: {calculate_sma(data, 200).iloc[-1]:.2f}, "
            f"EMA-50: {calculate_ema(data, 50).iloc[-1]:.2f}, EMA-200: {calculate_ema(data, 200).iloc[-1]:.2f}, "
            f"RSI: {calculate_rsi(data):.2f}."
        )
    except Exception as e:
        summary = f"Error generating summary: {e}"
    return summary

def build_stock_prompt(ticker, summary, price, volatility, ma_50, ma_200, ema_50, ema_200, rsi):
    """Construct prompt to request a recommendation from OpenAI."""
    return (
        f"You are a financial advisor. Based on the following technical data for {ticker},\n"
        f"start with a clear recommendation (Buy, Sell, or Hold) and then explain why.\n\n"
        f"Technical Summary:\n{summary}\n"
        f"Price: {price:.2f}, Volatility: {volatility:.2f},\n"
        f"SMA(50): {ma_50:.2f}, SMA(200): {ma_200:.2f},\n"
        f"EMA(50): {ema_50:.2f}, EMA(200): {ema_200:.2f}, RSI: {rsi:.2f}"
    )

def get_stock_recommendation(ticker, timeframe, openai_api_key):
    """Retrieve stock data, compute indicators, and get OpenAI recommendation."""
    period = {"short-term": "1y", "long-term": "15y"}.get(timeframe, timeframe)
    data = fetch_stock_data(ticker, period)
    if data.empty:
        return "No stock data available.", ""

    price = data['Close'].iloc[-1]
    volatility = calculate_volatility(data)
    ma_50 = calculate_sma(data, 50).iloc[-1]
    ma_200 = calculate_sma(data, 200).iloc[-1]
    ema_50 = calculate_ema(data, 50).iloc[-1]
    ema_200 = calculate_ema(data, 200).iloc[-1]
    rsi = calculate_rsi(data)
    summary = stock_data_summary(data)
    prompt = build_stock_prompt(ticker, summary, price, volatility, ma_50, ma_200, ema_50, ema_200, rsi)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip(), summary
    except Exception as e:
        return f"Error calling GenAI API: {e}", summary
