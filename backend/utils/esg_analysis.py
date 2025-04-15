# === esg_analysis.py ===
"""
Fetches ESG risk data from Yahoo Finance using yfinance,
and generates a sustainability assessment using OpenAI.
"""
import yfinance as yf
import openai
import json
import os
from datetime import datetime
import re

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
        peer_esg = esg_transposed.get("peerEsgScorePerformance", [None])[0] or {}
        peer_env = esg_transposed.get("peerEnvironmentPerformance", [None])[0] or {}
        peer_soc = esg_transposed.get("peerSocialPerformance", [None])[0] or {}
        peer_gov = esg_transposed.get("peerGovernancePerformance", [None])[0] or {}
        
        return {
            "Stock": ticker,
            "Total ESG Risk Score": esg_transposed.get("totalEsg", [None])[0],
            "ESG Performance": esg_transposed.get("esgPerformance", [None])[0],
            "Environmental Risk Score": esg_transposed.get("environmentScore", [None])[0],
            "Social Risk Score": esg_transposed.get("socialScore", [None])[0],
            "Governance Risk Score": esg_transposed.get("governanceScore", [None])[0],
            "Controversy Level": esg_transposed.get("highestControversy", [None])[0],
            "Peer Controversy Min": peer_controversy.get("min"),
            "Peer Controversy Avg": peer_controversy.get("avg"),
            "Peer Controversy Max": peer_controversy.get("max"),
            "Peer ESG Min": peer_esg.get("min"),
            "Peer ESG Avg": peer_esg.get("avg"),
            "Peer ESG Max": peer_esg.get("max"),
            "Peer Env Min": peer_env.get("min"),
            "Peer Env Avg": peer_env.get("avg"),
            "Peer Env Max": peer_env.get("max"),
            "Peer Social Min": peer_soc.get("min"),
            "Peer Social Avg": peer_soc.get("avg"),
            "Peer Social Max": peer_soc.get("max"),
            "Peer Gov Min": peer_gov.get("min"),
            "Peer Gov Avg": peer_gov.get("avg"),
            "Peer Gov Max": peer_gov.get("max"),
        }
    except Exception as e:
        return {"error": f"Error fetching ESG data for {ticker}: {e}"}

def generate_esg_assessment(esg_data, openai_api_key):
    """Generate an ESG assessment based on extracted ESG scores using OpenAI."""
    if "error" in esg_data:
        return esg_data["error"]

    prompt = (
    f"ESG Analysis for {esg_data['Stock']}:\n\n"

    "You must structure your response using the following exact section headers and format, without skipping or renaming any part. "
    "Bold the section titles using Markdown (**like this**), and write the content in full sentences, integrating all relevant data. "
    "Make sure the entire generated content is under 250 words.\n\n"

    f"1️⃣ **Total ESG Score:**\n\n"
    f"The company has a total ESG risk score of {esg_data.get('Total ESG Risk Score', 'N/A')}, "
    f"compared to its peers with a minimum of {esg_data.get('Peer ESG Min', 'N/A')}, "
    f"an average of {esg_data.get('Peer ESG Avg', 'N/A')}, and a maximum of {esg_data.get('Peer ESG Max', 'N/A')}. "
    f"The ESG performance is rated as {esg_data.get('ESG Performance', 'N/A')}. Provide a brief analysis, limit to 50 words.\n\n\n"

    f"2️⃣ **Breakdown of ESG Score:**\n\n"
    f"🌱 **Environment**\n\n"
    f"The environmental risk score is {esg_data.get('Environmental Risk Score', 'N/A')}, "
    f"with peers ranging from {esg_data.get('Peer Env Min', 'N/A')} to {esg_data.get('Peer Env Max', 'N/A')} and an average of {esg_data.get('Peer Env Avg', 'N/A')}.\n\n\n"

    f"🤝 **Social**\n\n"
    f"The social risk score is {esg_data.get('Social Risk Score', 'N/A')}, "
    f"compared to peer scores ranging from {esg_data.get('Peer Social Min', 'N/A')} to {esg_data.get('Peer Social Max', 'N/A')}, "
    f"with an average of {esg_data.get('Peer Social Avg', 'N/A')}. Provide a brief analysis.\n\n\n"

    f"🏛️ **Governance**\n\n"
    f"The governance risk score stands at {esg_data.get('Governance Risk Score', 'N/A')}, "
    f"while peers have a minimum of {esg_data.get('Peer Gov Min', 'N/A')}, an average of {esg_data.get('Peer Gov Avg', 'N/A')}, and a maximum of {esg_data.get('Peer Gov Max', 'N/A')}. Provide a brief analysis.\n\n\n"

    f"3️⃣ **Controversy Level:**\n\n"
    f"The company has a controversy level of {esg_data.get('Controversy Level', 'N/A')}, "
    f"with peers ranging from {esg_data.get('Peer Controversy Min', 'N/A')} to {esg_data.get('Peer Controversy Max', 'N/A')}, "
    f"and an average of {esg_data.get('Peer Controversy Avg', 'N/A')}. Provide a brief analysis, limit to 50 words.\n\n"
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

# Wrapper function
def get_esg_report(ticker, openai_api_key):
    esg_data = fetch_esg_data(ticker)
    return generate_esg_assessment(esg_data, openai_api_key)

# For faithfulness evaluation
def evaluate_esg_report_faithfulness(tickers, openai_api_key):
    """
    Evaluate the faithfulness of ESG reports for multiple tickers by comparing them to the source ESG data.
    Saves results as a JSON file in the 'faithfulness_eval' folder.
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    all_results = {}

    for ticker in tickers:
        esg_data = fetch_esg_data(ticker)
        generated_report = generate_esg_assessment(esg_data, openai_api_key)

        if "error" in esg_data or "Error" in generated_report:
            all_results[ticker] = {
                "Generated Report": generated_report,
                "Reference ESG Data": esg_data,
                "Faithfulness Evaluation": "Could not evaluate due to error in data or report generation."
            }
            continue

        reference_summary = "\n".join([
            f"{key}: {value}" for key, value in esg_data.items()
        ])

        evaluation_prompt = (
            f"Evaluate the faithfulness of the following ESG report based on the provided reference ESG data. "
            f"Faithfulness means how accurate and grounded the report is in the actual data. "
            f"Score it from 0 to 1 (1 being perfectly faithful), and provide a brief explanation.\n\n"
            f"Reference ESG Data:\n{reference_summary}\n\n"
            f"Generated ESG Report:\n{generated_report}"
        )

        try:
            openai.api_key = openai_api_key
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a critical ESG fact-checker assessing accuracy of ESG summaries."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3
            )
            evaluation_result = response.choices[0].message.content.strip()

            # Try to extract score and explanation
            score_match = re.search(r"Score\s*[:\-]?\s*([0-1](?:\.\d+)?)", evaluation_result)
            score = float(score_match.group(1)) if score_match else None

            # Remove the score line to get the explanation cleanly
            explanation = re.sub(r"Score\s*[:\-]?\s*[0-1](?:\.\d+)?\s*", "", evaluation_result, count=1, flags=re.IGNORECASE).strip()
            
            if explanation.lower().startswith("explanation:"):
                explanation = explanation[len("explanation:"):].strip()

            all_results[ticker] = {
                "Generated Report": generated_report,
                "Reference ESG Data": esg_data,
                "Faithfulness Evaluation": {
                    "Score": score,
                    "Explanation": explanation
                }
            }

        except Exception as e:
            all_results[ticker] = {
                "Generated Report": generated_report,
                "Reference ESG Data": esg_data,
                "Faithfulness Evaluation": f"Error evaluating faithfulness: {e}"
            }

    # Save to JSON file
    output_dir = os.path.join(os.path.dirname(__file__), "..", "faithfulness_eval")
    os.makedirs(output_dir, exist_ok=True)

    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_esg_faithfulness_eval.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(all_results, f, indent=4)

    return all_results


# # Uncomment the following lines to get evaluation report using the openai
# tickers_to_check = ["TSLA", "NVDA", "AAPL", "MSFT", "GOOGL ", "META", "AMZN", "PLTR ", "AMD", "NFLX"]
# evaluate_esg_report_faithfulness(tickers_to_check, "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")
