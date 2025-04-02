from flask import Flask, render_template, request, jsonify
from config import DEFAULT_PERIOD, OPENAI_API_KEY
from utils.stock_history import get_stock_recommendation
import openai
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    ticker = data.get("question", "").strip().upper()  # Expecting a ticker symbol, e.g., "AAPL"
    horizon = data.get("horizon", "")
    try:
        stock_rec, stock_summary = get_stock_recommendation(ticker, DEFAULT_PERIOD, OPENAI_API_KEY)
        holistic_report = (
            f"Holistic Recommendation for {ticker}:\n\n"
            f"Technical Analysis (Stock History):\n{stock_rec}\n\n"
            "ESG Analysis: [Pending]\n"
            "Financial Analysis: [Pending]\n"
            "News Analysis: [Pending]\n\n"
            "Final Decision: Based solely on technical analysis, a recommendation has been provided."
        )
        answer = holistic_report + "\n\nTechnical Breakdown:\n" + stock_summary
    except Exception as e:
        answer = f"Error generating recommendation for {ticker}: {e}"
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)

