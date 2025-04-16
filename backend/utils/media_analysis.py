
import os
import re
import json
import logging
import openai
import emoji
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
from database import db
from telethon.sessions import StringSession
from contractions import fix
import yfinance as yf
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Helper Functions
# -----------------------------
# def clean_headline(text):
#     """
#     Takes in a text
#     """
#     text = re.sub(r"<.*?>", "", text)
#     text = re.sub(r"[^a-zA-Z0-9.,!? ]", "", text)
#     return text.strip()

def filter_message_data(message):
    """
    Only get the relevant details from a raw scraped Telegram message
    """
    return {
        "id": message.get('id'),
        "date": message.get('date').isoformat() if message.get('date') else None,
        "message": message.get('message'),
    }

def ticker_to_shortname(ticker):
    """
    Takes in a ticker symbol and converts it to its corresponding short name
    """

    # Ensure company name is provided
    if not ticker:
        print("No ticker provided")
        return None
    
    # Custom overrides for known tickers (Google)
    custom_overrides = {
        "GOOGL": "Google",
        "GOOG": "Google"
    }

    if ticker.upper() in custom_overrides:
        return custom_overrides[ticker.upper()]

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        raw_name = info.get('shortName', 'N/A')
        for suffix in ["Inc.", "Incorporated", "Corp.", "Corporation", "Ltd.", "Limited", "PLC", ",", ".com", "Platforms", "Company"]:
            raw_name = raw_name.replace(suffix, "")
        return raw_name.strip()
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return None

def extract_ticker_specific_messages(company_name, headline_dict):
    """
    Takes in the company name (eg. Tesla) and all headlines scraped.
    Returns only ticker-specific headlines (ie. company name appears in headline)
    """

    # Ensure company name is provided
    if not company_name:
        print("No company name provided.")
        return {}
    
    # Extract the actual message content from the dictionary
    if headline_dict.get('message'):
        headline = headline_dict.get('message')
        first_part = headline.split("\n\n", 1)[0]
    
        # Check if the message contains the company name
        if re.search(rf"\b{re.escape(company_name)}\b", first_part, re.IGNORECASE):
            # If it's a match, keep only relevant data in the dictionary
            relevant_data = {key: headline_dict[key] for key in ['date', 'id'] if key in headline_dict}
            relevant_data['message'] = first_part
            return relevant_data
        

def clean_text(headlines):
    """
    Takes in a list of headlines and preprocesses them in place.
    Returns the list of cleaned headlines,
    """
    
    for i in range(len(headlines)):
        msg = headlines[i]
        if msg:
            msg = re.sub(r"<.*?>", "", msg)
            msg = re.sub(r"[^a-zA-Z0-9.,!? ]", "", msg)
            msg = msg.strip()
            msg = fix(msg)
            msg = emoji.demojize(msg)
            headlines[i] = msg
        else:
            headlines[i] = ""
    return headlines

# -----------------------------
# Initialise Telegram Client
# -----------------------------
async def initialise_telegram_client(api_id, api_hash, phone, username):
    client = TelegramClient(username, api_id, api_hash)
  
    # Start the client (this may prompt for login if necessary)
    async def start_client():
      await client.start(phone)

      # Check if user is authorized, otherwise log in
      if not await client.is_user_authorized():
          await client.send_code_request(phone)
          try:
              await client.sign_in(phone, input('Enter the code: '))
          except SessionPasswordNeededError:
              await client.sign_in(password=input('Password: '))

    # Run the client setup asynchronously
    await start_client()

    return client

# -----------------------------
# Scraping Function
# -----------------------------
async def scrape_telegram_headlines(client, ticker, days_to_scrape):
    """
    Returns a dictionary, with the key being the date in ISO format and the value being the headline
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
            print("No more messages. Stopping scraping...")
            break

        for message in history.messages:
            message = message.to_dict()
            filtered_message = filter_message_data(message)

            if not filtered_message:
                continue
            ticker_message = extract_ticker_specific_messages(company_name,filtered_message) # returns a dictionary
            
            if ticker_message:
                msg_date_str = ticker_message.get('date')
                if msg_date_str:
                    # To make compatible with Python's datetime, not a string anymore
                    msg_date = datetime.fromisoformat(msg_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    if msg_date < start_date:
                        return all_messages
                    all_messages.append({
                        "date": msg_date.isoformat(),
                        "message": ticker_message.get("message")
                    })

                    # Clean headlines
                    all_messages = clean_text([msg.get('message') for msg in all_messages if msg.get('message')])
                    
        offset_id = history.messages[-1].id

    return all_messages

# -----------------------------
# Summary Generator
# -----------------------------
async def generate_stock_summary(ticker, openai_api_key, headlines):
    if not headlines:
        return f"No recent headlines found for {ticker}."
    company_name = ticker_to_shortname(ticker)
    if not company_name:
        return f"Unable to determine company name for ticker: {ticker}"
    if not headlines:
        return f"No relevant headlines found for {ticker} ({company_name}) in the Telegram channel."

    headlines_str = "\n".join([f"- {headline}" for headline in headlines])
    headlines_str = headlines_str[:400_000]

    prompt = (
        f"Based on the following headlines which are the keys of the input dictionary that are 
        arranged from most recent to least recent,"
        f"generate an accurate summary of {ticker}'s market performance, "
        "highlighting trends, risks, or positive developments. **Include appropriate emojis as this is for a dashboard.** \n\n" +
        headlines_str +
        "\n\nKeep the summary short (3-5 sentences), focused on key insights."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial advisor specializing in technical analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        raw_output = response.choices[0].message.content.strip()

        # Remove any bold/emoji-styled header at the beginning, up to the first real sentence
        cleaned_output = re.sub(r"^.*?\*\*(.*?)\*\*.*?(?=[A-Z])", "", raw_output, flags=re.DOTALL)
        return cleaned_output.strip()
    
    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return "Unable to generate summary at this time due to an API error."
    

# --------------------------------------------
# Main Analysis Function, including evaluation
# --------------------------------------------
async def get_stock_summary(ticker, openai_api_key, evaluate=False):
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    username = os.getenv("USERNAME")
    phone = os.getenv("PHONE")

    today = datetime.today()
    headlines = db.get_headlines(ticker, today - relativedelta(months=6))
    last_headlines_date = datetime.fromisoformat(headlines[-1]["date"]).replace(tzinfo=None) if headlines else None
    logger.info(f"Found {len(headlines)} headlines for {ticker} in the last 6 months from {last_headlines_date}.")

    if len(headlines) == 0 or last_headlines_date <= (today - relativedelta(hours=6)):
        try:
            client = await initialise_telegram_client(api_id, api_hash, phone, username)
            days_to_scrape = (today - last_headlines_date).days + 1 if headlines else 180
            logger.info(f"Last headlines date: {last_headlines_date}. Scraping {days_to_scrape} days of headlines for {ticker}.")
            extra = await scrape_telegram_headlines(client, ticker, days_to_scrape)
            logger.info(f"Scraped {len(extra)} new headlines for {ticker} in the last {days_to_scrape} days.")
            db.save_headlines(ticker, extra)
            headlines.extend(extra)
            await client.disconnect()
        except Exception as e:
            logger.error(f"Error scraping headlines for {ticker}: {e}")

    summary = await generate_stock_summary(ticker, openai_api_key, headlines)
    
    # Do faithfulness evaluation
    if evaluate and isinstance(summary, str) and not summary.lower().startswith("unable"):

        evaluation_prompt = (
            f"Evaluate the faithfulness of the following media analysis or summary based on the provided reference media headlines. "
            f"Faithfulness means how accurate and grounded the report is in the actual data. "
            f"Score it from 0 to 1 (1 being perfectly faithful), and provide a brief explanation.\n\n"
            f"Reference Headlines:\n{headlines}\n\n"
            f"Generated Report:\n{summary}"
        )

        try:
            openai.api_key = openai_api_key
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a critical media headlines fact-checker assessing accuracy of media headline summaries."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3
            )
            evaluation_result = response.choices[0].message.content.strip()

            # Try to extract score and explanation
            score_match = re.search(r"Score\s*[:\-]?\s*([0-1](?:\.\d+)?)", evaluation_result)
            score = float(score_match.group(1)) if score_match else None

            explanation = re.sub(r"Score\s*[:\-]?\s*[0-1](?:\.\d+)?\s*", "", evaluation_result, count=1, flags=re.IGNORECASE).strip()
            if explanation.lower().startswith("explanation:"):
                explanation = explanation[len("explanation:"):].strip()

            # Save to JSON
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
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "w") as f:
                json.dump(results, f, indent=4)


        except Exception as e:
            print(f"Error evaluating faithfulness: {e}")

    return summary


# -----------------------------------------------------------------------------------------
# Evaluation Testing (Commented out by default, only run when evaluation needs to be done)
# -----------------------------------------------------------------------------------------
# if __name__ == "__main__":
#     import json
#     openai_api_key = os.getenv("OPENAI_API_KEY")
#     result = asyncio.run(get_stock_summary("AAPL", openai_api_key))
#     print(json.dumps(result, indent=2))
