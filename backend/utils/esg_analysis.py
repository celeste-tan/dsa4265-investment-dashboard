import yfinance as yf
import openai

def fetch_esg_data(ticker):
    """Fetch ESG scores using yfinance for a given stock ticker."""
    try:
        ticker_y = yf.Ticker(ticker)
        esg_df = ticker_y.sustainability

        if esg_df is None or esg_df.empty:
            return {"error": f"No ESG data available for {ticker}"}

        # Transpose and reset index
        esg_transposed = esg_df.transpose().reset_index(drop=True)

        # Extract peerHighestControversyPerformance
        peer_controversy_perf = esg_transposed.get("peerHighestControversyPerformance", [None])[0]
        peer_min = round(peer_controversy_perf.get("min"), 2) if peer_controversy_perf else None
        peer_avg = round(peer_controversy_perf.get("avg"), 2) if peer_controversy_perf else None
        peer_max = round(peer_controversy_perf.get("max"), 2) if peer_controversy_perf else None

        # Map relevant ESG scores
        esg_data = {
            "Stock": ticker,
            "Total ESG Risk Score": esg_transposed.get("totalEsg", [None])[0],
            "Environmental Risk Score": esg_transposed.get("environmentScore", [None])[0],
            "Social Risk Score": esg_transposed.get("socialScore", [None])[0],
            "Governance Risk Score": esg_transposed.get("governanceScore", [None])[0],
            "Controversy Level": esg_transposed.get("highestControversy", [None])[0],
            "Peer Controversy Min": peer_min,
            "Peer Controversy Avg": peer_avg,
            "Peer Controversy Max": peer_max
        }

        return esg_data

    except Exception as e:
        return {"error": f"Error fetching ESG data for {ticker}: {e}"}


def generate_esg_assessment(esg_data, openai_api_key):
    """Generate an ESG assessment based on extracted ESG scores using OpenAI."""
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
        "Based on the ESG risk scores and controversy level, provide an assessment of the company's sustainability and potential risks. Limit the output to 250 words."
    )

    try:
        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an ESG investment analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating ESG assessment: {e}"

def get_esg_report(ticker, openai_api_key):
    """Retrieve ESG scores and generate an AI-based ESG assessment for a given ticker."""
    esg_data = fetch_esg_data(ticker)
    esg_assessment = generate_esg_assessment(esg_data, openai_api_key)
    return esg_assessment

