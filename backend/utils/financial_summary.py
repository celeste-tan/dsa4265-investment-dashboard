import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import io
import base64

# ========== 1. Get Quarterly Financial Data ==========
def get_full_quarterly_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    income = ticker.quarterly_financials.T
    cashflow = ticker.quarterly_cashflow.T

    def safe_get(df, col):
        return df[col] if col in df.columns else pd.Series(dtype='float64')

    def format_dates(index):
        return [str(date.date()) for date in index]

    revenue = safe_get(income, "Total Revenue")
    net_income = safe_get(income, "Net Income")
    op_cf = safe_get(cashflow, "Operating Cash Flow")
    capex = safe_get(cashflow, "Capital Expenditure")

    # Compute Free Cash Flow only where both exist
    free_cf = op_cf.subtract(capex, fill_value=0)

    # Align indices — keep only quarters present in all
    common_index = revenue.index.intersection(net_income.index).intersection(free_cf.index)
    revenue = revenue[common_index]
    net_income = net_income[common_index]
    free_cf = free_cf[common_index]
    min_len = min(len(revenue), len(net_income), len(free_cf))
    df = pd.DataFrame({
        "Quarter": format_dates(revenue.index)[:min_len],
        "Revenue": revenue.values[:min_len],
        "Net Income": net_income.values[:min_len],
        "Free Cash Flow": free_cf.values[:min_len]
    })
    #print("✅ Final financial chart data:")
    #print(df.head())



    return df.sort_values(by="Quarter")


# ========== 2. Slice Quarterly Data by Period ==========
def filter_financial_data_by_period(df, period="1y"):
    period_map = {
        "1y": 4,
        "2y": 8,
        "5y": 20,
        "max": len(df)
    }
    num_quarters = period_map.get(period, 4)
    return df.tail(num_quarters)

# ========== 3. Generate Summary ==========
def generate_financial_summary(df, ticker):
    if len(df) < 2:
        return "Not enough data to generate summary."
    df=df.dropna()
    start = df.iloc[0]
    end = df.iloc[-1]

    pct_rev = ((end["Revenue"] - start["Revenue"]) / start["Revenue"]) * 100
    pct_income = ((end["Net Income"] - start["Net Income"]) / start["Net Income"]) * 100
    pct_fcf = ((end["Free Cash Flow"] - start["Free Cash Flow"]) / start["Free Cash Flow"]) * 100

    summary = (
        f"Over the past {len(df)} quarters, {ticker.upper()}’s revenue changed by {pct_rev:.2f}%, "
        f"net income changed by {pct_income:.2f}%, and free cash flow changed by {pct_fcf:.2f}%.\n\n"
        f"Latest Quarter Values:\n"
        f"- Revenue: ${end['Revenue']:,.0f}\n"
        f"- Net Income: ${end['Net Income']:,.0f}\n"
        f"- Free Cash Flow: ${end['Free Cash Flow']:,.0f}"
    )
    return summary

# ========== 4. AI Commentary ==========
def generate_ai_investment_commentary(summary_text, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a professional financial analyst. Based on the following quarterly financial summary, write an investment commentary in 3-4 sentences. 
Provide a Buy, Sell, or Hold recommendation based on the trends in revenue, net income, and free cash flow.

Summary:
{summary_text}

Commentary:
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

# ========== 5. Chart as Base64 Image ==========
"""
def plot_financial_trends(df, ticker_symbol):
    plt.figure(figsize=(12, 6))
    plt.plot(df["Quarter"], df["Revenue"], marker='o', label="Revenue")
    plt.plot(df["Quarter"], df["Net Income"], marker='o', label="Net Income")
    plt.plot(df["Quarter"], df["Free Cash Flow"], marker='o', label="Free Cash Flow")
    plt.title(f"{ticker_symbol.upper()} Quarterly Financial Trends")
    plt.xlabel("Quarter")
    plt.ylabel("Amount (USD)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return encoded
"""
# ========== 6. Unified Interface ==========
def generate_full_financial_summary(ticker, openai_api_key, period="1y"):
    df_all = get_full_quarterly_data(ticker)
    df = filter_financial_data_by_period(df_all, period)

    if df.empty:
        raise ValueError("No financial data available.")

    summary = generate_financial_summary(df, ticker)
    commentary = generate_ai_investment_commentary(summary, openai_api_key)
    chart_base64 = plot_financial_trends(df, ticker)

    return summary, commentary, chart_base64, df.to_dict(orient="records")


def filter_financial_data_by_period(df, period="max"):
    period_map = {
        "1y": 4,
        "2y": 8,
        "5y": 20,
        "10y": 40,
        "15y": 60,
        "max": len(df)
    }
    num_quarters = period_map.get(period, 4)
    return df.tail(num_quarters)

