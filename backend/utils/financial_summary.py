# === financial_summary.py ===
"""
Downloads quarterly and annual financial data from Yahoo Finance (via yfinance),
generates summaries of revenue, net income, and free cash flow trends,
and produces an AI-generated investment commentary using OpenAI.
"""

# -----------------------------
# Imports
# -----------------------------
import yfinance as yf
import pandas as pd
import openai
import os
import json
import re
from datetime import datetime

# -----------------------------
# Download Quarterly Financial Data
# -----------------------------
def get_full_quarterly_data(ticker_symbol):
    """
    Retrieve quarterly income and cash flow data, then compute free cash flow.
    Returns a DataFrame with Revenue, Net Income, and Free Cash Flow.
    """
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

    # Align all series to common date index
    common_index = revenue.index.intersection(net_income.index).intersection(free_cf.index)
    revenue, net_income, free_cf = revenue[common_index], net_income[common_index], free_cf[common_index]

    df = pd.DataFrame({
        "Quarter": [str(date.date()) for date in revenue.index],
        "Revenue": revenue.values,
        "Net Income": net_income.values,
        "Free Cash Flow": free_cf.values
    })
    df.dropna(subset=["Revenue", "Net Income", "Free Cash Flow"], inplace=True)

    return df.sort_values(by="Quarter")


# -----------------------------
# Download Annual Financial Data
# -----------------------------
def get_full_annual_data(ticker_symbol):
    """
    Retrieve annual income and cash flow data, then compute free cash flow.
    Returns a DataFrame with Revenue, Net Income, and Free Cash Flow.
    """
    ticker = yf.Ticker(ticker_symbol)
    income = ticker.financials.T
    cashflow = ticker.cashflow.T

    def safe_get(df, col):
        return df[col] if col in df.columns else pd.Series(dtype='float64')

    revenue = safe_get(income, "Total Revenue")
    net_income = safe_get(income, "Net Income")
    op_cf = safe_get(cashflow, "Operating Cash Flow")
    capex = safe_get(cashflow, "Capital Expenditure")
    free_cf = op_cf.subtract(capex, fill_value=0)

    # Align all series to common date index
    common_index = revenue.index.intersection(net_income.index).intersection(free_cf.index)
    revenue, net_income, free_cf = revenue[common_index], net_income[common_index], free_cf[common_index]

    df = pd.DataFrame({
        "Year": [str(date.year) for date in revenue.index],
        "Revenue": revenue.values,
        "Net Income": net_income.values,
        "Free Cash Flow": free_cf.values
    })
    df.dropna(subset=["Revenue", "Net Income", "Free Cash Flow"], inplace=True)

    return df.sort_values(by="Year")


# -----------------------------
# Filter Data by Time Horizon
# -----------------------------
def filter_financial_data_by_period(df, period="1y"):
    """
    Slice DataFrame by period (1y, 2y, 5y, etc.).
    Periods are converted to a number of quarters.
    """
    period_map = {
        "1y": 4, "2y": 8, "5y": 20,
        "10y": 40, "15y": 60, "max": len(df)
    }
    num_quarters = period_map.get(period, 4)
    return df.tail(num_quarters)


# -----------------------------
# Generate Human-Readable Summary
# -----------------------------
def generate_financial_summary(df, ticker):
    """
    Summarise revenue, net income, and free cash flow trends over time.
    Includes both percentage and CAGR trends.
    """
    if len(df.dropna()) < 2:
        return "Not enough data to generate summary."

    df = df.dropna()
    start, end = df.iloc[0], df.iloc[-1]
    periods = len(df)

    def pct_change(start_val, end_val):
        return ((end_val - start_val) / start_val) * 100 if start_val else 0

    def annualized_change(start_val, end_val, periods):
        if start_val <= 0 or periods < 2:
            return 0
        return ((end_val / start_val) ** (1 / (periods - 1)) - 1) * 100

    rev_change = pct_change(start['Revenue'], end['Revenue'])
    ni_change = pct_change(start['Net Income'], end['Net Income'])
    fcf_change = pct_change(start['Free Cash Flow'], end['Free Cash Flow'])

    rev_cagr = annualized_change(start['Revenue'], end['Revenue'], periods)
    ni_cagr = annualized_change(start['Net Income'], end['Net Income'], periods)
    fcf_cagr = annualized_change(start['Free Cash Flow'], end['Free Cash Flow'], periods)

    trend = lambda pct: "increased" if pct > 0 else "decreased" if pct < 0 else "remained flat"

    summary = (
        f"Over the past {periods} quarters, {ticker.upper()}’s financials have shown the following trends:\n\n"
        f"- **Revenue** has {trend(rev_change)} by {abs(rev_change):.2f}%, averaging a CAGR of {rev_cagr:.2f}%.\n"
        f"- **Net Income** has {trend(ni_change)} by {abs(ni_change):.2f}%, with an annualized change of {ni_cagr:.2f}%.\n"
        f"- **Free Cash Flow** has {trend(fcf_change)} by {abs(fcf_change):.2f}%, with a CAGR of {fcf_cagr:.2f}%.\n\n"
        f"📊 **Latest Reported Values:**\n"
        f"- Revenue: **${end['Revenue']:,.0f}**\n"
        f"- Net Income: **${end['Net Income']:,.0f}**\n"
        f"- Free Cash Flow: **${end['Free Cash Flow']:,.0f}**\n\n"
        f"📈 These trends may suggest {'growth momentum' if rev_cagr > 0 else 'financial headwinds'} in recent periods, "
        f"but further qualitative analysis (e.g. margin trends or R&D expenses) is recommended."
    )

    return summary


# -----------------------------
# Generate AI Commentary
# -----------------------------
def generate_ai_investment_commentary(summary_text, api_key):
    """
    Generate a buy/hold/sell investment commentary using GPT.
    """
    openai.api_key = api_key
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


# -----------------------------
# Unified Summary + Commentary Interface
# -----------------------------
def generate_full_financial_summary(ticker, openai_api_key, period="1y"):
    """
    Unified function to return summary, commentary, and raw data records.
    """
    df_all = get_full_quarterly_data(ticker)
    df = filter_financial_data_by_period(df_all, period)

    if df.empty:
        raise ValueError("No financial data available.")

    summary = generate_financial_summary(df, ticker)
    commentary = generate_ai_investment_commentary(summary, openai_api_key)
    return summary, commentary, None, df.to_dict(orient="records")


# -----------------------------
# Faithfulness Evaluation
# -----------------------------
def evaluate_financial_commentary_faithfulness(tickers, openai_api_key, period="1y"):
    """
    Evaluate the faithfulness of AI commentaries across multiple tickers.
    Scores and explanations are saved to a JSON report.
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    all_results = {}

    for ticker in tickers:
        try:
            df_all = get_full_quarterly_data(ticker)
            df = filter_financial_data_by_period(df_all, period)

            if df.empty:
                raise ValueError("No financial data available.")

            summary = generate_financial_summary(df, ticker)
            commentary = generate_ai_investment_commentary(summary, openai_api_key)

            if "Error" in commentary:
                raise ValueError(commentary)

            eval_prompt = (
                f"Evaluate the faithfulness of the following AI-generated investment commentary based on the financial summary provided. "
                f"Faithfulness means how accurate and grounded the commentary is in the summary data. "
                f"Score it from 0 to 1 (1 being perfectly faithful), and provide a brief explanation.\n\n"
                f"Financial Summary:\n{summary}\n\n"
                f"Generated Commentary:\n{commentary}"
            )

            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a critical financial fact-checker assessing commentary for data accuracy."},
                    {"role": "user", "content": eval_prompt}
                ],
                temperature=0.3
            )

            evaluation_result = response.choices[0].message.content.strip()

            # Extract faithfulness score and clean explanation
            score_match = re.search(r"Score\s*[:\-]?\s*([0-1](?:\.\d+)?)", evaluation_result)
            score = float(score_match.group(1)) if score_match else None
            explanation = re.sub(r"Score\s*[:\-]?\s*[0-1](?:\.\d+)?\s*", "", evaluation_result, count=1, flags=re.IGNORECASE).strip()

            if explanation.lower().startswith("explanation:"):
                explanation = explanation[len("explanation:"):].strip()

            all_results[ticker] = {
                "Generated Commentary": commentary,
                "Reference Financial Summary": summary,
                "Faithfulness Evaluation": {
                    "Score": score,
                    "Explanation": explanation
                }
            }

        except Exception as e:
            all_results[ticker] = {
                "Generated Commentary": str(e),
                "Reference Financial Summary": "Unavailable",
                "Faithfulness Evaluation": f"Error evaluating faithfulness: {e}"
            }

    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), "..", "faithfulness_eval")
    os.makedirs(output_dir, exist_ok=True)

    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_financial_faithfulness_eval.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(all_results, f, indent=4)

    return all_results


# -----------------------------
# Optional Evaluation (Disabled by Default)
# -----------------------------
# tickers_to_check = ["TSLA", "NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "PLTR", "AMD", "NFLX"]
# openai_api_key = os.getenv("OPENAI_API_KEY")
# evaluate_financial_commentary_faithfulness(tickers_to_check, openai_api_key)
