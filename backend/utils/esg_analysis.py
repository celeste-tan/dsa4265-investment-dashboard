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

# print(fetch_esg_data("AAPL"))

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

# print(generate_esg_assessment(fetch_esg_data("AAPL"), "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"))

# Wrapper
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
        #print(f"Evaluating {ticker}...")

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

    #print(f"\nFaithfulness evaluations saved to: {filepath}")
    return all_results


# Example usage
tickers_to_check = ["TSLA", "NVDA", "AAPL", "SPY", "QQQ", "META", "AMZN", "TQQQ", "AMD", "NFLX"]
evaluate_esg_report_faithfulness(tickers_to_check, "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")
