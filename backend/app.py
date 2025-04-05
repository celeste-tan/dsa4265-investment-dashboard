# from flask import Flask, render_template, request, jsonify
# from backend.config import DEFAULT_PERIOD, OPENAI_API_KEY, ESG_API_TOKEN
# from utils.stock_history import get_stock_recommendation
# import openai
# import asyncio
# from utils.esg_analysis import get_esg_report, fetch_esg_data
# from utils.media_sentiment_analysis import get_stock_summary
# from dotenv import load_dotenv

# load_dotenv()

# app = Flask(__name__)

# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/ask", methods=["POST"])
# def ask():
#     data = request.get_json()
#     ticker = data.get("question", "").strip().upper()  # Expecting a ticker symbol, e.g., "AAPL"
#     horizon = data.get("horizon", "")
#     try:
#         stock_rec, stock_summary = get_stock_recommendation(ticker, DEFAULT_PERIOD, OPENAI_API_KEY)

#         # Get ESG analysis
#         esg_data = fetch_esg_data(ticker, ESG_API_TOKEN)  # Fetch raw ESG scores
#         esg_analysis = get_esg_report(ticker, ESG_API_TOKEN, OPENAI_API_KEY)

#         # Extract ESG scores for technical breakdown
#         total_esg_score = esg_data.get("Total ESG Risk Score", "N/A")
#         environmental_score = esg_data.get("Environmental Risk Score", "N/A")
#         social_score = esg_data.get("Social Risk Score", "N/A")
#         governance_score = esg_data.get("Governance Risk Score", "N/A")
#         controversy_value = esg_data.get("Controversy Level", {}).get("Value", "N/A")
#         controversy_description = esg_data.get("Controversy Level", {}).get("Description", "N/A")

#         # Get news headlines analysis
#         news_summary = asyncio.run(get_stock_summary(ticker, OPENAI_API_KEY))


#         holistic_report = (
#             f"Holistic Recommendation for {ticker}:\n\n"
#             f"Technical Analysis (Stock History):\n{stock_rec}\n\n"
#             f"ESG Analysis:\n{esg_analysis}\n\n"
#             "Financial Analysis: [Pending]\n"
#             f"News Analysis: \n{news_summary}\n\n"
#             "Final Decision: Based solely on technical analysis, a recommendation has been provided."
#         )

#         # Technical Breakdown with ESG Scores
#         technical_breakdown = (
#             f"\n\nTechnical Breakdown:\n"
#             f"{stock_summary}\n\n"
#             f"ESG Scores:\n"
#             f"- Total ESG Risk Score: {total_esg_score}\n"
#             f"- Environmental Risk Score: {environmental_score}\n"
#             f"- Social Risk Score: {social_score}\n"
#             f"- Governance Risk Score: {governance_score}\n"
#             f"- Controversy Level: {controversy_value} ({controversy_description})"
#         )

#         answer = holistic_report + technical_breakdown

#     except Exception as e:
#         answer = f"Error generating recommendation for {ticker}: {e}"
#     return jsonify({"answer": answer})

# @app.route("/esg", methods=["POST"])
# def get_esg():
#     data = request.get_json()
#     ticker = data.get("ticker", "").strip().upper()

#     try:
#         esg_data = fetch_esg_data(ticker, ESG_API_TOKEN)
#         esg_analysis = get_esg_report(ticker, ESG_API_TOKEN, OPENAI_API_KEY)

#         return jsonify({
#             "esg_scores": esg_data,
#             "esg_analysis": esg_analysis
#         })

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# if __name__ == "__main__":
#     app.run(debug=True)


from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from utils.esg_analysis import get_esg_report, fetch_esg_data
from config import DEFAULT_PERIOD, OPENAI_API_KEY, ESG_API_TOKEN
from utils.stock_history import get_stock_recommendation
import openai
import asyncio
from utils.media_sentiment_analysis import get_stock_summary
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

# ESG ANALYSIS
@app.route("/api/esg-scores", methods=["POST"])
def get_esg_scores():
    """New route that returns only the individual ESG scores."""
    data = request.json
    ticker = data.get("ticker", "").upper()
    print(f"Received ticker: {ticker}")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    # Fetch ESG data for the ticker
    esg_data = fetch_esg_data(ticker, ESG_API_TOKEN)
    
    if "error" in esg_data:
        return jsonify({"error": esg_data["error"]}), 400

    # Extract just the scores
    esg_scores = {
        "Total ESG Risk Score": esg_data.get("Total ESG Risk Score"),
        "Environmental Risk Score": esg_data.get("Environmental Risk Score"),
        "Social Risk Score": esg_data.get("Social Risk Score"),
        "Governance Risk Score": esg_data.get("Governance Risk Score"),
        "Controversy Value": esg_data.get("Controversy Level", {}).get("Value", "N/A"),
        "Controversy Description": esg_data.get("Controversy Level", {}).get("Description", "N/A")
    }

    print(f"Extracted ESG Scores: {esg_scores}")
    
    return jsonify({"esg_scores": esg_scores})

@app.route("/api/esg-gen-report", methods=["POST"])
def get_esg():
    data = request.json
    ticker = data.get("ticker", "").upper()
    print(f"Received ticker: {ticker}")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400

    report = get_esg_report(ticker, ESG_API_TOKEN, OPENAI_API_KEY)
    print(f"Generated ESG Report: {report}")
    return jsonify({"report": report})


# MEDIA SENTIMENT ANALYSIS
@app.route("/api/media-sentiment-summary", methods=["POST"])
def get_media_summary():
    data = request.json
    ticker = data.get("ticker", "").upper()
    print(f"Received ticker: {ticker}")

    if not ticker:
        return jsonify({"error": "Missing ticker symbol"}), 400
    
    summary = asyncio.run(get_stock_summary(ticker, OPENAI_API_KEY))
    print(summary)
    return jsonify({"summary": summary})

if __name__ == "__main__":
    app.run(debug=True)
