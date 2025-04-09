# === holistic_summary.py ===
"""
Main orchestration module that aggregates technical, financial,
ESG, and media signals into a final investment recommendation.
"""
import os
import openai
from dotenv import load_dotenv
import logging

# Local analysis modules
from utils.stock_history import get_stock_recommendation
from utils.esg_analysis import get_esg_report
from utils.financial_summary import generate_full_financial_summary
from utils.media_sentiment_analysis import get_stock_summary

# Load environment variable
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Aggregated Recommendation Generator 
async def get_holistic_recommendation(ticker, timeframe="short-term"):
    """
    Generate final recommendation using:
    - Technical indicators
    - ESG data
    - Financials
    - Media sentiment
    """
    logging.info(f"Generating holistic recommendation for {ticker} ({timeframe})")

    stock_rec, stock_summary = get_stock_recommendation(ticker, timeframe, openai_api_key)
    esg_analysis = get_esg_report(ticker, openai_api_key)

    try:
        fin_summary, fin_commentary, _, _ = generate_full_financial_summary(ticker, openai_api_key, period="1y")
    except Exception as e:
        fin_commentary = f"Error fetching financial summary: {e}"

    try:
        media_summary = await get_stock_summary(ticker, openai_api_key)
    except Exception as e:
        media_summary = f"Error fetching media sentiment: {e}"

    # Prompt construction
    prompt = (
        f"You are a financial advisor. Summarise the investment outlook for '{ticker}' across different signals:\n\n"
        f"Technical Insight:\n{stock_rec}\n\n"
        f"ESG Insight:\n{esg_analysis}\n\n"
        f"Financial Insight:\n{fin_commentary}\n\n"
        f"Media Sentiment Insight:\n{media_summary}\n\n"
        f"Return output as concise bullet points with signals and a final recommendation:\n"
        f"- Stock: <Signal> — <Short reason>\n"
        f"- ESG: <Signal> — <Short reason>\n"
        f"- Financials: <Signal> — <Short reason>\n"
        f"- Media: <Signal> — <Short reason>\n"
        f"Final Recommendation: <Buy/Hold/Sell> — <Rationale>"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst summarising multiple investment signals."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating final insight: {e}"
