# === media_analysis.py ===
"""
Scrapes financial headlines from Telegram using Telethon,
filters for ticker-specific relevance, cleans the text,
and uses OpenAI to generate media sentiment summaries with optional faithfulness evaluation.
"""

# -----------------------------
# Imports
# -----------------------------
import os
import re
import json
import logging
import openai
import emoji
import yfinance as yf
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel

# Local modules
from database import db
from contractions import fix

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Helper Functions
# -----------------------------
def filter_message_data(message):
    """Extracts only the relevant fields from a raw Telegram message."""
    return {
        "id": message.get('id'),
        "date": message.get('date').isoformat() if message.get('date') else None,
        "message": message.get('message'),
    }

def ticker_to_shortname(ticker):
    """Fetches the short name of a company given its stock ticker."""
    if not ticker:
        print("No ticker provided")
        return None

    overrides = {"GOOGL": "Google", "GOOG": "Google"}
    if ticker.upper() in overrides:
        return overrides[ticker.upper()]

    try:
        stock = yf.Ticker(ticker)
        name = stock.info.get('shortName', 'N/A')
        for suffix in ["Inc.", "Incorporated", "Corp.", "Corporation", "Ltd.", "Limited", "PLC", ",", ".com", "Platforms", "Company"]:
            name = name.replace(suffix, "")
        return name.strip()
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return None

def extract_ticker_specific_messages(company_name, headline_dict):
    """Extracts only headlines that explicitly mention the company name."""
    if not company_name:
        return {}

    message = headline_dict.get('message', "")
    first_part = message.split("\n\n", 1)[0]
    if re.search(rf"\b{re.escape(company_name)}\b", first_part, re.IGNORECASE):
        return {
            "date": headline_dict.get("date"),
            "id": headline_dict.get("id"),
            "message": first_part
        }

def clean_text(headlines):
    """Cleans and standardises a list of headlines."""
    for i in range(len(headlines)):
        msg = headlines[i]
        if msg:
            msg = re.sub(r"<.*?>", "", msg)
            msg = re.sub(r"[^a-zA-Z0-9.,!? ]", "", msg)
            msg = fix(msg)
            msg = emoji.demojize(msg)
            headlines[i] = msg.strip()
        else:
            headlines[i] = ""
    return headlines

# -----------------------------
# Telegram Client Initialization
# -----------------------------
async def initialise_telegram_client(api_id, api_hash, phone, username):
    """Starts and authenticates a Telethon client."""
    client = TelegramClient(username, api_id, api_hash)

    async def start_client():
        await client.start(phone)
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            try:
                await client.sign_in(phone, input('Enter the code: '))
            except SessionPasswordNeededError:
                await client.sign_in(password=input('Password: '))

    await start_client()
    return client

# -----------------------------
# Scrape Headlines from Telegram
# -----------------------------
async def scrape_telegram_headlines(client, ticker, days_to_scrape):
    """
    Scrapes Telegram headlines from the configured channel and filters for ticker relevance.
    """
    user_input_channel = '@BizTimes'
    entity = PeerChannel(int(user_input_channel)) if user_input_channel.isdigit() else user_input_channel
    my_channel = await client.get_entity(entity)
    company_name = ticker_to_shortname(ticker)

    offset_id = 0
    limit = 100
    all_messages = []
    today = datetime.today()
    start_date = today - relativedelta(days=days_to_scrape)

    while True:
        history = await client(GetHistoryRequest(
            peer=my_channel,
            offset_id=offset_id,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))

        if not history.messages:
            break

        for message in history.messages:
            filtered = filter_message_data(message.to_dict())
            if not filtered:
                continue

            ticker_msg = extract_ticker_specific_messages(company_name, filtered)
            if ticker_msg:
                msg_date = datetime.fromisoformat(ticker_msg['date'].replace("Z", "+00:00")).replace(tzinfo=None)
                if msg_date < start_date:
                    return all_messages

                all_messages.append({
                    "date": msg_date.isoformat(),
                    "message": ticker_msg["message"]
                })

        offset_id = history.messages[-1].id

    # Clean all collected headlines
    cleaned = clean_text([msg["message"] for msg in all_messages if msg.get("message")])
    for i in range(len(cleaned)):
        all_messages[i]["message"] = cleaned[i]

    return all_messages

# -----------------------------
# Generate OpenAI Summary
# -----------------------------
async def generate_stock_summary(ticker, openai_api_key, headlines):
    """Summarises a list of headlines into a short dashboard-friendly insight with emojis."""
    if not headlines:
        return f"No recent headlines found for {ticker}."

    company_name = ticker_to_shortname(ticker)
    if not company_name:
        return f"Unable to determine company name for ticker: {ticker}"

    headlines_str = "\n".join([f"- {h}" for h in headlines])[:400_000]

    prompt = (
        f"Based on the following headlines, generate an accurate summary of {ticker}'s market performance, "
        "highlighting trends, risks, or positive developments. **Include appropriate emojis for a dashboard.**\n\n"
        f"{headlines_str}\n\n"
        "Keep the summary short (3–5 sentences), focused on key insights."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial advisor specializing in technical analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        raw_output = response.choices[0].message.content.strip()
        cleaned_output = re.sub(r"^.*?\*\*(.*?)\*\*.*?(?=[A-Z])", "", raw_output, flags=re.DOTALL)
        return cleaned_output.strip()
    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return "Unable to generate summary at this time due to an API error."

# -----------------------------
# Main Analysis + Evaluation
# -----------------------------
async def get_stock_summary(ticker, openai_api_key, evaluate=False):
    """
    Retrieves and updates media headlines, generates summary, and optionally evaluates faithfulness.
    """
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    username = os.getenv("USERNAME")
    phone = os.getenv("PHONE")
    today = datetime.today()

    # Load cached headlines
    headlines = db.get_headlines(ticker, today - relativedelta(months=6))
    last_date = datetime.fromisoformat(headlines[-1]["date"]).replace(tzinfo=None) if headlines else None
    logger.info(f"Found {len(headlines)} headlines for {ticker} since {last_date}.")

    # Scrape new headlines if needed
    if len(headlines) == 0 or last_date <= (today - relativedelta(hours=6)):
        try:
            client = await initialise_telegram_client(api_id, api_hash, phone, username)
            days = (today - last_date).days + 1 if headlines else 180
            logger.info(f"Scraping {days} days of headlines for {ticker}.")
            extra = await scrape_telegram_headlines(client, ticker, days)
            logger.info(f"Scraped {len(extra)} new headlines.")
            db.save_headlines(ticker, extra)
            headlines.extend(extra)
            await client.disconnect()
        except Exception as e:
            logger.error(f"Error scraping headlines for {ticker}: {e}")

    summary = await generate_stock_summary(ticker, openai_api_key, [msg['message'] for msg in headlines])

    # Evaluate summary faithfulness
    if evaluate and isinstance(summary, str) and not summary.lower().startswith("unable"):
        evaluation_prompt = (
            f"Evaluate the faithfulness of the following media analysis based on the provided headlines. "
            f"Faithfulness means how accurate and grounded the summary is in the actual headlines. "
            f"Score it from 0 to 1 (1 being perfectly faithful), and provide a brief explanation.\n\n"
            f"Reference Headlines:\n{headlines}\n\n"
            f"Generated Report:\n{summary}"
        )

        try:
            openai.api_key = openai_api_key
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a critical media fact-checker."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3
            )
            eval_result = response.choices[0].message.content.strip()

            score_match = re.search(r"Score\s*[:\-]?\s*([0-1](?:\.\d+)?)", eval_result)
            score = float(score_match.group(1)) if score_match else None
            explanation = re.sub(r"Score\s*[:\-]?\s*[0-1](?:\.\d+)?\s*", "", eval_result, count=1, flags=re.IGNORECASE).strip()

            if explanation.lower().startswith("explanation:"):
                explanation = explanation[len("explanation:"):].strip()

            results = {
                "Ticker": ticker,
                "Generated Analysis": summary,
                "Reference Headlines": headlines,
                "Faithfulness Evaluation": {
                    "Score": score,
                    "Explanation": explanation
                }
            }

            output_dir = os.path.join(os.path.dirname(__file__), "..", "faithfulness_eval")
            os.makedirs(output_dir, exist_ok=True)

            filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{ticker}_media_eval.json"
            with open(os.path.join(output_dir, filename), "w") as f:
                json.dump(results, f, indent=4)

        except Exception as e:
            print(f"Error evaluating faithfulness: {e}")

    return summary

# -----------------------------
# Optional Evaluation (Disabled)
# -----------------------------
# if __name__ == "__main__":
#     import asyncio
#     openai_api_key = os.getenv("OPENAI_API_KEY")
#     result = asyncio.run(get_stock_summary("AAPL", openai_api_key))
#     print(json.dumps(result, indent=2))
