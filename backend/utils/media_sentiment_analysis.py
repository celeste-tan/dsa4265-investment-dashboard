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
from datetime import date, datetime, timezone
from dateutil.parser import parse as parse_date  # Changed from datetime import
from dateutil.relativedelta import relativedelta
from contractions import fix
from dotenv import load_dotenv
import os
import yfinance as yf
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global Telegram client (initialized when needed)
client = None

############ Helper Functions ############

def filter_message_data(message):
    try:
        message_date = message.get('date')
        if message_date:
            if isinstance(message_date, datetime):
                # Already a datetime object
                formatted_date = message_date.isoformat()
            else:
                # Parse string date
                formatted_date = parse_date(str(message_date)).isoformat()
        else:
            formatted_date = None
            
        return {
            "id": message.get('id'),
            "date": formatted_date,
            "message": message.get('message'),
        }
    except Exception as e:
        logger.error(f"Error filtering message data: {e}")
        return {
            "id": message.get('id'),
            "date": None,
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
        logger.error(f"Error fetching info for {ticker}: {e}")
        return None

def extract_ticker_specific_headlines(company_name, headlines):
    if not company_name:
        logger.warning("No company name provided for headline filtering")
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

############ Telegram Functions ############

async def initialize_telegram_client():
    """Initialize and return a Telegram client"""
    global client
    
    if client and client.is_connected():
        return client
        
    try:
        client = TelegramClient(
            StringSession(os.getenv("STRING_SESSION")),
            int(os.getenv("API_ID")),
            os.getenv("API_HASH")
        )
        await client.start()
        if not client.is_connected():
            raise ConnectionError("Failed to connect to Telegram")
        logger.info("Telegram client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Telegram client: {e}")
        raise

async def scrape_telegram_headlines():
    """Scrape headlines from predefined Telegram channel"""
    global client
    
    try:
        # Initialize client with proper connection management
        if not client or not client.is_connected():
            client = await initialize_telegram_client()
        
        user_input_channel = os.getenv("TELEGRAM_CHANNEL", "@BizTimes")
        
        try:
            entity = PeerChannel(int(user_input_channel)) if user_input_channel.isdigit() else user_input_channel
            my_channel = await client.get_entity(entity)
        except ValueError:
            logger.error(f"Invalid channel identifier: {user_input_channel}")
            return []

        offset_id = 0
        limit = 100
        all_messages = []
        today = datetime.now(timezone.utc)
        start_date = today - relativedelta(months=6)

        while True:
            try:
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
            except Exception as e:
                logger.error(f"Error fetching message history: {e}")
                break

            if not history.messages:
                logger.info("No more messages found in channel")
                break

            messages_added = False
            for message in history.messages:
                try:
                    filtered_message = filter_message_data(message.to_dict())
                    msg_date_str = filtered_message.get('date')
                    
                    if msg_date_str:
                        try:
                            msg_date = parse_date(msg_date_str)
                            if msg_date.tzinfo is None:
                                msg_date = msg_date.replace(tzinfo=timezone.utc)
                        except ValueError as e:
                            logger.error(f"Failed to parse datetime: {msg_date_str}. Error: {e}")
                            continue
                            
                        if msg_date < start_date:
                            logger.info(f"Reached cutoff date, returning {len(all_messages)} messages")
                            return all_messages
                            
                    all_messages.append(filtered_message)
                    messages_added = True
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue

            if not messages_added:
                break

            offset_id = history.messages[-1].id

        channel_name = get_channel(user_input_channel)
        file_name = f'{channel_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        try:
            with open(file_name, 'w', encoding='utf-8') as outfile:
                json.dump(all_messages, outfile, cls=DateTimeEncoder, indent=4, ensure_ascii=False)
            logger.info(f"Saved {len(all_messages)} messages to {file_name}")
        except Exception as e:
            logger.error(f"Error saving messages to file: {e}")

        return all_messages

    except Exception as e:
        logger.error(f"Error scraping Telegram channel: {e}")
        return []
    finally:
        # Don't disconnect here - let the calling function manage the connection
        pass

############ Analysis Functions ############

async def generate_stock_summary(ticker, openai_api_key, headlines):
    if not headlines:
        logger.warning(f"No headlines found for {ticker}")
        return f"No recent headlines found for {ticker}."
        
    headlines_split = split_into_headlines(headlines)
    company_name = ticker_to_shortname(ticker)
    
    if not company_name:
        logger.warning(f"Could not resolve company name for {ticker}")
        return f"Unable to determine company name for ticker: {ticker}"
        
    headlines_to_use = extract_ticker_specific_headlines(company_name, headlines_split)
    
    if not headlines_to_use:
        logger.warning(f"No relevant headlines for {company_name} ({ticker})")
        return f"No relevant headlines found for {ticker} ({company_name}) in the Telegram channel."
        
    headlines_to_use = clean_text(headlines_to_use)

    prompt = (
        f"Analyze these {ticker} ({company_name}) headlines and:\n"
        "1. Assign sentiment (positive/negative/neutral) to each\n"
        "2. Identify key themes\n"
        "3. Provide 2-3 sentence summary of market perception\n\n"
        "Headlines:\n" + 
        "\n".join([f"- {headline}" for headline in headlines_to_use])
    )

    try:
        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[ 
                {"role": "system", "content": "You are a financial analyst summarizing market sentiment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=256
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "Unable to generate summary due to API error."

############ Main Function ############

nest_asyncio.apply()

async def get_stock_summary(ticker, openai_api_key):
    """Main function to get stock summary"""
    global client
    
    try:
        # Initialize client if needed
        if not client:
            client = await initialize_telegram_client()
        
        # Scrape headlines
        headlines = await scrape_telegram_headlines()
        
        # Generate summary
        summary = await generate_stock_summary(ticker, openai_api_key, headlines)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in get_stock_summary: {e}")
        return f"Error generating summary: {str(e)}"
    finally:
        # Clean up client connection
        if client and client.is_connected():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting Telegram client: {e}")
            client = None