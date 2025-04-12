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

load_dotenv()

############ Helper Functions ############

def filter_message_data(message):
    return {
        "id": message.get('id'),
        "date": message.get('date').isoformat() if message.get('date') else None,
        "message": message.get('message'),
    }

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, bytes):
            return list(o)
        return json.JSONEncoder.default(self, o)

def get_channel(name):
    match = re.search(r't\.me/([A-Za-z0-9_]+)', name)
    return match.group(1) if match else name

def split_into_headlines(messages):
    for msg in messages:
        if not msg.get('message'):
            msg['headline'] = ""
            msg['subheadline'] = ""
            continue
        components = msg['message'].split("\n\n", 1)
        msg['headline'] = components[0]
        msg['subheadline'] = components[1] if len(components) > 1 else ""
    return messages

def ticker_to_shortname(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        raw_name = info.get('shortName', 'N/A')
        for suffix in ["Inc.", "Incorporated", "Corp.", "Corporation", "Ltd.", "Limited", "PLC", ","]:
            raw_name = raw_name.replace(suffix, "")
        return raw_name.strip()
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return None

def extract_ticker_specific_headlines(company_name, headlines):
    if not company_name:
        print(f"No company name provided.")
        return []
    return [
        msg.get('headline') for msg in headlines
        if msg.get('headline') and re.search(rf"\b{re.escape(company_name)}\b", msg['headline'], re.IGNORECASE)
    ]

def clean_text(headlines):
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

# ✅ Use StringSession here
async def initialise_telegram_client(api_id, api_hash, string_session):
    client = TelegramClient(StringSession(string_session), api_id, api_hash)
    await client.start()
    return client

async def scrape_telegram_headlines(client, ticker):
    user_input_channel = '@BizTimes'
    entity = PeerChannel(int(user_input_channel)) if user_input_channel.isdigit() else user_input_channel
    my_channel = await client.get_entity(entity)

    offset_id = 0
    limit = 100
    all_messages = []
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

    channel_name = get_channel(user_input_channel)
    file_name = f'{channel_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(file_name, 'w', encoding='utf-8') as outfile:
        json.dump(all_messages, outfile, cls=DateTimeEncoder, indent=4, ensure_ascii=False)

    print(f"Messages saved to {file_name}")
    return all_messages

async def generate_stock_summary(ticker, openai_api_key, headlines):
    if not headlines:
        return f"No recent headlines found for {ticker}."
    headlines_split = split_into_headlines(headlines)
    company_name = ticker_to_shortname(ticker)
    if not company_name:
        return f"Unable to determine company name for ticker: {ticker}"
    headlines_to_use = extract_ticker_specific_headlines(company_name, headlines_split)
    if not headlines_to_use:
        return f"No relevant headlines found for {ticker} ({company_name}) in the Telegram channel."
    headlines_to_use = clean_text(headlines_to_use)

    prompt = (
        f"Based on the following headlines that are arranged from most recent to least recent, assign a sentiment to each headline - either positive, negative or neutral. "
        f"Then, generate an accurate summary of {ticker}'s market performance, "
        "highlighting trends, risks, or positive developments.\n\n" +
        "\n".join([f"- {headline}" for headline in headlines_to_use]) +
        "\n\nKeep the summary short (2-3 sentences), focused on key insights, and acknowledge the limitations of headlines as investment indicators."
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
        return response.choices[0].message.content.strip()
    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return "Unable to generate summary at this time due to an API error."

# Main Function
nest_asyncio.apply()

async def get_stock_summary(ticker, openai_api_key):
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    string_session = os.getenv("STRING_SESSION")

    client = await initialise_telegram_client(api_id, api_hash, string_session)
    headlines = await scrape_telegram_headlines(client)
    summary = await generate_stock_summary(ticker, openai_api_key, headlines)
    await client.disconnect()
    return summary
