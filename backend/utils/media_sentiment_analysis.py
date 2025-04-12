
import os
import re
import json
import openai
import asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.sessions import StringSession
from telethon.tl.types import PeerChannel

load_dotenv()

# Helper functions
def clean_headline(text):
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^a-zA-Z0-9.,!? ]", "", text)
    return text.strip()

async def initialise_telegram_client(api_id, api_hash, string_session):
    client = TelegramClient(StringSession(string_session), api_id, api_hash)
    await client.start()
    return client

async def scrape_telegram_headlines(client):
    channel_name = '@BizTimes'
    entity = PeerChannel(int(channel_name)) if channel_name.isdigit() else channel_name
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
            break

        for message in history.messages:
            msg_dict = message.to_dict()
            msg_date = msg_dict.get('date')
            if msg_date and msg_date.replace(tzinfo=None) < start_date:
                return all_messages
            all_messages.append({
                "date": msg_dict.get("date").isoformat(),
                "message": msg_dict.get("message")
            })

        offset_id = history.messages[-1].id

    return all_messages

async def generate_stock_summary(ticker, openai_api_key, headlines):
    if not headlines:
        return f"No recent headlines found for {ticker}."
    cleaned = [clean_headline(h["message"]) for h in headlines if h.get("message")]
    joined = "\n".join([f"- {line}" for line in cleaned if line])
    prompt = f"""Based on the headlines below, summarize the market sentiment for {ticker}:
{joined}

Summarize in 2-3 sentences."""
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

async def get_stock_summary(ticker, openai_api_key):
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    string_session = os.getenv("STRING_SESSION")

    client = await initialise_telegram_client(api_id, api_hash, string_session)
    headlines = await scrape_telegram_headlines(client)
    summary = await generate_stock_summary(ticker, openai_api_key, headlines)
    await client.disconnect()
    return summary
