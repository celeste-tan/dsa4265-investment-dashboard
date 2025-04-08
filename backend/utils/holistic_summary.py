import os
import sys
import asyncio
from dotenv import load_dotenv
import openai
import logging

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

# === Imports from your backend modules ===
from backend.utils.stock_history import get_stock_recommendation
from backend.utils.esg_analysis import get_esg_report
from backend.utils.financial_summary import generate_full_financial_summary
from backend.utils.media_sentiment_analysis import get_stock_summary

# === Load API Key ===
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# === Main Holistic Generator ===
async def get_holistic_recommendation(ticker, timeframe="short-term"):
    logging.info(f"Generating holistic recommendation for {ticker} ({timeframe})")


    # Technical stock recommendation
    stock_rec, stock_summary = get_stock_recommendation(ticker, timeframe, openai_api_key)

    # ESG analysis
    esg_analysis = get_esg_report(ticker, openai_api_key)

    # Financial summary and commentary
    try:
        fin_summary, fin_commentary, _, _ = generate_full_financial_summary(ticker, openai_api_key, period="1y")
    except Exception as e:
        fin_commentary = f"Error fetching financial summary: {e}"

    # Media sentiment from Telegram headlines
    try:
        media_summary = await get_stock_summary(ticker, openai_api_key)
    except Exception as e:
        media_summary = f"Error fetching media sentiment: {e}"

    # Generate concise summary using OpenAI
    prompt = (
        f"You are a financial assistant. Summarize the investment outlook for '{ticker}' for professional users in a dashboard view.\n\n"
        f"Your task is to extract key insights and signals from the data below:\n\n"
        f"Technical Insight:\n{stock_rec}\n\n"
        f"ESG Insight:\n{esg_analysis}\n\n"
        f"Financial Insight:\n{fin_commentary}\n\n"
        f"Media Sentiment Insight:\n{media_summary}\n\n"
        f"Return your response as concise bullet points with signals:\n"
        f"- Stock: <Signal> — <Short reason>\n"
        f"- ESG: <Signal> — <Short reason>\n"
        f"- Financials: <Signal> — <Short reason>\n"
        f"- Media: <Signal> — <Short reason>\n"
        f"Final Recommendation: <Buy/Hold/Sell> — <Final short rationale>"
    )

    try:
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst summarizing insights for an investment dashboard."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating final insight: {e}"
"""
# === CLI Testing ===
if __name__ == "__main__":
    ticker = "MSFT"
    print("\n⏳ Loading holistic insight...")

    final_report = asyncio.run(get_holistic_recommendation(ticker, timeframe="short-term"))
    print("\n" + final_report)
"""