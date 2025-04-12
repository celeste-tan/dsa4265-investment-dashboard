from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

# Generates a session string so there is no need to continuously key in a code everytime the scraping is done
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Logging in...")
    client.start(phone)
    print("Your session string is:\n")
    print(client.session.save())
