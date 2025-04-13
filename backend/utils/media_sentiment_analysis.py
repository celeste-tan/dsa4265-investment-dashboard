
import os
import re
import json
import logging
import openai
import asyncio
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.sessions import StringSession
from telethon.tl.types import PeerChannel
from database import db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper functions
def clean_headline(text):
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^a-zA-Z0-9.,!? ]", "", text)
    return text.strip()

async def initialise_telegram_client(api_id, api_hash, string_session):
    client = TelegramClient(StringSession(string_session), api_id, api_hash)
    await client.start()
    return client

async def scrape_telegram_headlines(client, days_to_scrape):
    channel_name = '@BizTimes'
    entity = PeerChannel(int(channel_name)) if channel_name.isdigit() else channel_name
    my_channel = await client.get_entity(entity)

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

    today = datetime.today()
    headlines = db.get_headlines(ticker, today - relativedelta(months=6))
    logger.info(f"Found {len(headlines)} headlines for {ticker} in the last 6 months.")
    last_headlines_date = datetime.fromisoformat(headlines[-1]["date"]).replace(tzinfo=None) if headlines else None

    if not headlines or last_headlines_date <= (today - relativedelta(hours=6)):
        client = await initialise_telegram_client(api_id, api_hash, string_session)
        days_to_scrape = (today - last_headlines_date).days + 1 if headlines else 180
        logger.info(f"Last headlines date: {last_headlines_date}. Scraping {days_to_scrape} days of headlines for {ticker}.")
        extra = await scrape_telegram_headlines(client, days_to_scrape)
        logger.info(f"Scraped {len(extra)} new headlines for {ticker} in the last 6 months.")
        db.save_headlines(ticker, extra)
        headlines.extend(extra)
        await client.disconnect()

    summary = await generate_stock_summary(ticker, openai_api_key, headlines)
    return summary
