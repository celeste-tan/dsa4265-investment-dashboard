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

    prompt = (f"""
    You are a financial analyst AI. Given the stock ticker '{ticker}', provide a concise investment summary across five dimensions. Your response must be no more than 135 words total.

    Include the following sections in **exactly** this format:

    ✅ **Final Recommendation: <Buy/Hold/Sell>**  
    One-line overall recommendation based on all signals combined.

    • 📈 **Stock Performance: <Buy/Hold/Sell>**  
    Explain briefly using indicators like price, volatility, SMA/EMA, and RSI.

    • 🌿 **ESG Insight: <Positive/Neutral/Negative>**  
    Comment on ESG scores and any notable sustainability, governance, or social risks.

    • 💰 **Financial Health: <Strong/Moderate/Weak>**  
    Summarise trends in revenue, net income, and cash flow strength.

    • 📰 **Media Sentiment: <Positive/Neutral/Negative>**  
    Summarise the tone and implications of recent news sentiment.

    Use natural language and markdown bold formatting as shown. Be concise but informative.

    Now generate your holistic summary based on the following. If any of them have an error, set them to N/A.

    Technical Insight:  
    {stock_rec}

    ESG Insight:  
    {esg_analysis}

    Financial Insight:  
    {fin_commentary}

    Media Sentiment Insight:  
    {media_summary}
    """
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
