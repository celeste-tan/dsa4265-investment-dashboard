# === financial_summary.py ===
"""
Downloads quarterly financial data from Yahoo Finance (via yfinance),
generates a summary of revenue, net income, and free cash flow trends,
and produces an investment commentary with OpenAI.
"""
import yfinance as yf
import pandas as pd
import openai

# Download Quarterly Financial Data
def get_full_quarterly_data(ticker_symbol):
    """Retrieve income and cash flow data and compute free cash flow."""
    ticker = yf.Ticker(ticker_symbol)
    income = ticker.quarterly_financials.T
    cashflow = ticker.quarterly_cashflow.T

    def safe_get(df, col):
        return df[col] if col in df.columns else pd.Series(dtype='float64')

    revenue = safe_get(income, "Total Revenue")
    net_income = safe_get(income, "Net Income")
    op_cf = safe_get(cashflow, "Operating Cash Flow")
    capex = safe_get(cashflow, "Capital Expenditure")
    free_cf = op_cf.subtract(capex, fill_value=0)

    common_index = revenue.index.intersection(net_income.index).intersection(free_cf.index)
    revenue, net_income, free_cf = revenue[common_index], net_income[common_index], free_cf[common_index]

    df = pd.DataFrame({
        "Quarter": [str(date.date()) for date in revenue.index],
        "Revenue": revenue.values,
        "Net Income": net_income.values,
        "Free Cash Flow": free_cf.values
    })
    return df.sort_values(by="Quarter")

# Filter Data by Time Horizon
def filter_financial_data_by_period(df, period="1y"):
    period_map = {
        "1y": 4, "2y": 8, "5y": 20,
        "10y": 40, "15y": 60, "max": len(df)
    }
    num_quarters = period_map.get(period, 4)
    return df.tail(num_quarters)

# Generate Human-Readable Summary
def generate_financial_summary(df, ticker):
    if len(df.dropna()) < 2:
        return "Not enough data to generate summary."

    df = df.dropna()
    start, end = df.iloc[0], df.iloc[-1]

    def pct_change(start_val, end_val):
        return ((end_val - start_val) / start_val) * 100 if start_val else 0

    summary = (
        f"Over the past {len(df)} quarters, {ticker.upper()}’s revenue changed by {pct_change(start['Revenue'], end['Revenue']):.2f}%, "
        f"net income by {pct_change(start['Net Income'], end['Net Income']):.2f}%, and free cash flow by {pct_change(start['Free Cash Flow'], end['Free Cash Flow']):.2f}%\n\n"
        f"Latest Quarter Values:\n"
        f"- Revenue: ${end['Revenue']:,.0f}\n"
        f"- Net Income: ${end['Net Income']:,.0f}\n"
        f"- Free Cash Flow: ${end['Free Cash Flow']:,.0f}"
    )
    return summary

# Generate AI Commentary
def generate_ai_investment_commentary(summary_text, api_key):
    prompt = (
        "You are a professional financial analyst. Based on the following financial summary, "
        "write a 3-4 sentence investment commentary with a Buy, Sell, or Hold recommendation.\n\n"
        f"Summary:\n{summary_text}\n\nCommentary:"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating commentary: {e}"

# Unified Summary Interface
def generate_full_financial_summary(ticker, openai_api_key, period="1y"):
    df_all = get_full_quarterly_data(ticker)
    df = filter_financial_data_by_period(df_all, period)

    if df.empty:
        raise ValueError("No financial data available.")

    summary = generate_financial_summary(df, ticker)
    commentary = generate_ai_investment_commentary(summary, openai_api_key)
    return summary, commentary, None, df.to_dict(orient="records")
