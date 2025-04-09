# === esg_analysis.py ===
"""
Fetches ESG risk data from Yahoo Finance using yfinance,
and generates a sustainability assessment using OpenAI.
"""
import yfinance as yf
import openai

# ESG Data Collection
def fetch_esg_data(ticker):
    """Download ESG scores and controversy performance."""
    try:
        ticker_y = yf.Ticker(ticker)
        esg_df = ticker_y.sustainability

        if esg_df is None or esg_df.empty:
            return {"error": f"No ESG data available for {ticker}"}

        esg_transposed = esg_df.transpose().reset_index(drop=True)
        peer_controversy = esg_transposed.get("peerHighestControversyPerformance", [None])[0] or {}

        return {
            "Stock": ticker,
            "Total ESG Risk Score": esg_transposed.get("totalEsg", [None])[0],
            "Environmental Risk Score": esg_transposed.get("environmentScore", [None])[0],
            "Social Risk Score": esg_transposed.get("socialScore", [None])[0],
            "Governance Risk Score": esg_transposed.get("governanceScore", [None])[0],
            "Controversy Level": esg_transposed.get("highestControversy", [None])[0],
            "Peer Controversy Min": peer_controversy.get("min"),
            "Peer Controversy Avg": peer_controversy.get("avg"),
            "Peer Controversy Max": peer_controversy.get("max")
        }
    except Exception as e:
        return {"error": f"Error fetching ESG data for {ticker}: {e}"}

# ESG Interpretation via LLM 
def generate_esg_assessment(esg_data, openai_api_key):
    """Summarise ESG profile using OpenAI."""
    if "error" in esg_data:
        return esg_data["error"]

    prompt = (
        f"ESG Analysis for {esg_data['Stock']}:\n"
        f"Total ESG Risk Score: {esg_data.get('Total ESG Risk Score', 'N/A')}\n"
        f"Environmental Risk Score: {esg_data.get('Environmental Risk Score', 'N/A')}\n"
        f"Social Risk Score: {esg_data.get('Social Risk Score', 'N/A')}\n"
        f"Governance Risk Score: {esg_data.get('Governance Risk Score', 'N/A')}\n"
        f"Controversy Level: {esg_data.get('Controversy Level', 'N/A')}\n"
        f"Peer Controversy Min: {esg_data.get('Peer Controversy Min', 'N/A')}\n"
        f"Peer Controversy Avg: {esg_data.get('Peer Controversy Avg', 'N/A')}\n"
        f"Peer Controversy Max: {esg_data.get('Peer Controversy Max', 'N/A')}\n\n"
        "Provide a 2-3 sentence ESG assessment and potential risks."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a sustainability analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating ESG assessment: {e}"

# Wrapper
def get_esg_report(ticker, openai_api_key):
    esg_data = fetch_esg_data(ticker)
    return generate_esg_assessment(esg_data, openai_api_key)
