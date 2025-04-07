from datetime import datetime
from pandas.tseries.offsets import BDay
import yfinance as yf
import openai
from ..database import db

# -----------------------------
# Stock Data Functions
# -----------------------------
def get_date_range(period):
    """Return the start and end dates for a given period using trading days."""
    today = datetime.today()
    if period == "1d":
        start = today - BDay(1)
    elif period == "5d":
        start = today - BDay(5)
    elif period == "1mo":
        start = today - BDay(21)
    elif period == "3mo":
        start = today - BDay(63)
    elif period == "1y":
        start = today - BDay(252)
    elif period == "5y":
        start = today - BDay(252*5)
    elif period == "10y":
        start = today - BDay(252*10)
    elif period == "15y":
        start = today - BDay(252*15)
    else:
        raise ValueError("Invalid period specified")
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

def fetch_stock_data(ticker_symbol, period):
    """Fetch stock history for the given ticker and period."""
    ticker = yf.Ticker(ticker_symbol)
    if period == "1d":
        data = ticker.history(period="1d", interval="1m")
    else:
        start_date, end_date = get_date_range(period)
        data = ticker.history(start=start_date, end=end_date)
    return data

# -----------------------------
# Technical Indicator Calculations
# -----------------------------
def calculate_sma(data, window=50):
    return data['Close'].rolling(window=window).mean()

def calculate_ema(data, window=50):
    return data['Close'].ewm(span=window, adjust=False).mean()

def calculate_volatility(data):
    data['Daily_Return'] = data['Close'].pct_change()
    volatility = data['Daily_Return'].std() * (252 ** 0.5)
    return volatility

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    return rsi

def stock_data_summary(data):
    """Generate a summary from stock data including technical indicators."""
    if data.empty:
        return "No data available to summarize."
    try:
        start_price = data['Close'].iloc[0]
        end_price = data['Close'].iloc[-1]
        pct_change = ((end_price - start_price) / start_price) * 100
        volatility = calculate_volatility(data)
        ma_50 = calculate_sma(data, window=50).iloc[-1]
        ma_200 = calculate_sma(data, window=200).iloc[-1]
        ema_50 = calculate_ema(data, window=50).iloc[-1]
        ema_200 = calculate_ema(data, window=200).iloc[-1]
        rsi = calculate_rsi(data)
        summary = (
            f"Price changed by {pct_change:.2f}%. "
            f"Volatility: {volatility:.2f}, 50-day SMA: {ma_50:.2f}, 200-day SMA: {ma_200:.2f}, "
            f"50-day EMA: {ema_50:.2f}, 200-day EMA: {ema_200:.2f}, RSI: {rsi:.2f}."
        )
    except Exception as e:
        summary = f"Error generating summary: {e}"
    return summary

def build_stock_prompt(ticker, summary, price, volatility, ma_50, ma_200, ema_50, ema_200, rsi):
    prompt = (
        f"You are a financial advisor. Based on the following technical data for {ticker}, "
        f"start with a clear recommendation (Buy, Sell, or Hold) and then explain why in less than 250 words.\n\n"

        f"Give the recommendation in the first sentence clearly.\n\n"

        f"Technical Summary for {ticker}:\n"
        f"{summary}\n"
        f"Current Price: {price:.2f}\n"
        f"Volatility: {volatility:.2f}\n"
        f"50-day SMA: {ma_50:.2f}, 200-day SMA: {ma_200:.2f}\n"
        f"50-day EMA: {ema_50:.2f}, 200-day EMA: {ema_200:.2f}\n"
        f"RSI: {rsi:.2f}\n\n"

        f"Use these indicators to evaluate price trends, momentum, and market sentiment. "
        f"Then conclude with your rationale behind the recommendation."
    )
    return prompt

def get_stock_recommendation(ticker, timeframe, openai_api_key):
    # Determine period based on timeframe type
    if timeframe == "short-term":
        period = "1y"
    elif timeframe == "long-term":
        period = "15y"  # default to 15y for long-term view; frontend can pass more specific values like '5y', '10y', etc.
    else:
        period = timeframe  # assume frontend passed a valid yfinance period

    data = fetch_stock_data(ticker, period)
    if data.empty:
        return "No stock data available.", ""

    price = data['Close'].iloc[-1]
    volatility = calculate_volatility(data)
    ma_50 = calculate_sma(data, window=50).iloc[-1]
    ma_200 = calculate_sma(data, window=200).iloc[-1]
    ema_50 = calculate_ema(data, window=50).iloc[-1]
    ema_200 = calculate_ema(data, window=200).iloc[-1]
    rsi = calculate_rsi(data)
    summary = stock_data_summary(data)
    prompt = build_stock_prompt(ticker, summary, price, volatility, ma_50, ma_200, ema_50, ema_200, rsi)

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial advisor specializing in technical analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        recommendation = response.choices[0].message.content.strip()
    except Exception as e:
        recommendation = f"Error calling GenAI API: {e}"

    return recommendation, summary
