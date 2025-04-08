import nest_asyncio
import asyncio
import datetime
import openai
import emoji
import json
import re
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
from telethon.sessions import StringSession
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from contractions import fix
from dotenv import load_dotenv
import os
import yfinance as yf

# Load environment variable from .env file
load_dotenv()

############ Helper Functions ############

# Function to parse only required attributes
def filter_message_data(message):
    return {
        "id": message.get('id'),
        "date": message.get('date').isoformat() if message.get('date') else None,
        "message": message.get('message'),
        # Add other fields as needed
    }

# DateTimeEncoder to handle custom JSON serialization
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, bytes):
            return list(o)
        return json.JSONEncoder.default(self, o)

# Function to get the channel name and use it as file name
def get_channel(name):
    # Extract the channel name from URLs like https://t.me/TheStraitsTimes
    match = re.search(r't\.me/([A-Za-z0-9_]+)', name)
    return match.group(1) if match else name

# Only get the headlines portion, because the message will include links which is not helpful in sentiment analysis
def split_into_headlines(messages):
  for msg in messages:
    if not msg.get('message'):  # Check if 'message' is None or missing
        msg['headline'] = ""
        msg['subheadline'] = ""
        continue

    components = msg['message'].split("\n\n", 1)

    msg['headline'] = components[0]
    msg['subheadline'] = components[1] if len(components) > 1 else ""
  return messages

# Mapping of ticker to company name
def ticker_to_shortname(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        raw_name = info.get('shortName', 'N/A')

        # Clean common suffixes
        for suffix in ["Inc.", "Incorporated", "Corp.", "Corporation", "Ltd.", "Limited", "PLC", ","]:
            raw_name = raw_name.replace(suffix, "")
        clean_name = raw_name.strip()
        
        return clean_name
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return None

# Filter for stock-specific headlines
def extract_ticker_specific_headlines(ticker, headlines):
  company_name = ticker_to_shortname(ticker)
  if not company_name:
    print(f"No mapping found for ticker: {ticker}")
    return []
  
  relevant_headlines = [
      msg.get('headline') for msg in headlines
      if msg.get('headline') and re.search(rf"\b{company_name}\b", msg['headline'], re.IGNORECASE)
  ]
  return relevant_headlines

# Clean after filtering for stock-specific headlines
def clean_text(headlines):
  for msg in headlines:
    if msg:
        # Remove HTML tags
        msg = re.sub(r"<.*?>", "", msg)
        # Remove special characters
        msg = re.sub(r"[^a-zA-Z0-9.,!? ]", "", msg)
        # Remove extra spaces
        msg = msg.strip()
        # Expand contractions
        msg = fix(msg)
        # Handle emojis
        msg = emoji.demojize(msg)

  return headlines


# Initialise and returns telegram client
async def initialise_telegram_client(api_id, api_hash, phone, username):
    client = TelegramClient(username, api_id, api_hash)
    # client = TelegramClient("sessions/coleincidence", api_id, api_hash)
  
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

#     # Run the client setup asynchronously
#   asyncio.run(start_client())
              
    # Await instead of asyncio.run()
    await start_client()
    return client

async def scrape_telegram_headlines(client):
        """
        Scrapes recent messages from a Telegram channel.
        """
        user_input_channel = '@BizTimes'

        entity = PeerChannel(int(user_input_channel)) if user_input_channel.isdigit() else user_input_channel
        my_channel = await client.get_entity(entity)

        offset_id = 0
        limit = 100
        all_messages = []

        # start date: 6 months ago from today
        today = datetime.today()
        start_date = today - relativedelta(months=6)

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
                filtered_message = filter_message_data(message.to_dict())

                msg_date_str = filtered_message.get('date')
                msg_date = datetime.fromisoformat(msg_date_str.replace("Z", "+00:00")).replace(tzinfo=None)

                if msg_date < start_date:
                    return all_messages

                all_messages.append(filtered_message)

            offset_id = history.messages[-1].id

        # Save JSON file
        channel_name = get_channel(user_input_channel)
        file_name = f'{channel_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(file_name, 'w', encoding='utf-8') as outfile:
            json.dump(all_messages, outfile, cls=DateTimeEncoder, indent=4, ensure_ascii=False)

        print(f"Messages saved to {file_name}")
        return all_messages


# Function to generate stock summary using openAI
async def generate_stock_summary(ticker, openai_api_key, headlines):
    """
    Generates stock summary based on scraped headlines.
    """
    if not headlines:
        return f"No recent headlines found for {ticker}."

    # Step 1: Split into headline and subheadline
    headlines_split = split_into_headlines(headlines)

    # Step 2: Filter headlines mentioning the stock ticker
    headlines_to_use = extract_ticker_specific_headlines(ticker, headlines_split)

    if not headlines_to_use:
        return f"No relevant headlines found for {ticker} in the Telegram channel."

    # Step 3: Clean headlines
    headlines_to_use = clean_text(headlines_to_use)

    # Step 4: Generate AI summary
    prompt = (
        f"Based on the following headlines, generate an accurate summary of {ticker}'s market performance, "
        "highlighting trends, risks, or positive developments. However, also mention that news headlines alone "
        "are limited and are not sufficient to determine whether one should invest in the stock.\n\n" +
        "\n".join([f"- {headline}" for headline in headlines_to_use]) +
        "\n\nKeep the summary short (2-3 sentences), focused on key insights, and acknowledge the limitations of headlines as investment indicators."
    )

    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # or whatever model you're using
        messages=[
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": prompt}
        ]
    )

    return response["choices"][0]["message"]["content"]


# Main function
nest_asyncio.apply()

async def get_stock_summary(ticker, openai_api_key):
    # Step 1: Initialize the Telegram client
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE")
    username = os.getenv("USERNAME")

    client = await initialise_telegram_client(api_id, api_hash, phone, username)

    # Step 2: Scrape Telegram headlines
    headlines = await scrape_telegram_headlines(client)

    # Step 3: Get the stock ticker from user input

    # Step 4: Generate stock summary using the scraped headlines
    summary = await generate_stock_summary(ticker, openai_api_key, headlines)

    await client.disconnect()
    return summary
