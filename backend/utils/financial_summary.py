import yfinance as yf

def generate_summary(ticker_symbol):
    import pandas as pd

    ticker = yf.Ticker(ticker_symbol)

    # Pull and transpose financials
    income = ticker.financials.T
    balance = ticker.balance_sheet.T
    cashflow = ticker.cashflow.T

    # Helper to get data safely
    def safe_get(df, col):
        return df[col].dropna().tolist() if col in df.columns else []

    # Extract time series data (most recent 3 years)
    revenue = safe_get(income, "Total Revenue")[:3]
    net_income = safe_get(income, "Net Income")[:3]
    gross_profit = safe_get(income, "Gross Profit")[:3]
    operating_income = safe_get(income, "Operating Income")[:3]
    cash = safe_get(balance, "Cash And Cash Equivalents")[:3]
    debt = safe_get(balance, "Total Debt")[:3]
    equity = safe_get(balance, "Common Stock Equity")[:3]
    op_cf = safe_get(cashflow, "Operating Cash Flow")[:3]
    capex = safe_get(cashflow, "Capital Expenditure")[:3]
    free_cf = [op - cap for op, cap in zip(op_cf, capex)] if op_cf and capex else []

    # Derived metrics
    gross_margin = [(gp / rev) * 100 for gp, rev in zip(gross_profit, revenue)] if revenue and gross_profit else []
    operating_margin = [(oi / rev) * 100 for oi, rev in zip(operating_income, revenue)] if revenue and operating_income else []

    # Growth calculation helper
    def pct_change(current, previous):
        if current is not None and previous is not None and previous != 0:
            return round(100 * (current - previous) / abs(previous), 2)
        return None

    # Format number
    def fmt(n):
        return f"${n/1e9:.1f}B" if n else "N/A"

    # Generate dynamic trend paragraph
    def generate_trend_paragraph():
        if len(revenue) < 2 or len(net_income) < 2:
            return "Not enough historical data to generate trend analysis."

        rev_growth = pct_change(revenue[0], revenue[1])
        ni_growth = pct_change(net_income[0], net_income[1])
        fcf_growth = pct_change(free_cf[0], free_cf[1]) if len(free_cf) >= 2 else None
        gm_change = pct_change(gross_margin[0], gross_margin[1]) if len(gross_margin) >= 2 else None
        om_change = pct_change(operating_margin[0], operating_margin[1]) if len(operating_margin) >= 2 else None

        paragraph = f"""
Over the past year, {ticker_symbol.upper()}’s total revenue {'increased' if rev_growth > 0 else 'declined'} by {abs(rev_growth)}%, 
from {fmt(revenue[1])} to {fmt(revenue[0])}. Net income {'rose' if ni_growth > 0 else 'fell'} by {abs(ni_growth)}%, 
reaching {fmt(net_income[0])}. The company’s gross margin {'improved' if gm_change and gm_change > 0 else 'contracted' if gm_change else 'remained stable'}, 
changing by {abs(gm_change)} percentage points to {round(gross_margin[0], 2)}%, while operating margin {'increased' if om_change and om_change > 0 else 'decreased' if om_change else 'held steady'}, 
now at {round(operating_margin[0], 2)}%.

{ticker_symbol.upper()} also generated {fmt(free_cf[0])} in free cash flow, a {abs(fcf_growth)}% {'increase' if fcf_growth > 0 else 'decline'} from the prior year. 
These figures suggest that while {ticker_symbol.upper()} remains highly profitable, its most recent performance reflects {'continued growth' if rev_growth > 0 and ni_growth > 0 else 'some softening in financial momentum'}. 
Investors should watch for how macroeconomic conditions and product cycles affect future revenue and margin expansion.
"""
        return paragraph.strip()

    return generate_trend_paragraph()
