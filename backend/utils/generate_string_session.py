# === generate_string_session.py ===
"""
Generates a reusable Telegram session string using Telethon.
This avoids the need to re-enter the OTP each time for authenticated scraping.
"""

# -----------------------------
# Imports
# -----------------------------
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

# -----------------------------
# Generate Session String
# -----------------------------
# Creates a session string that can be reused to authenticate with Telegram.
# This prevents repeated login prompts and streamlines scraping workflows.
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Logging in...")
    client.start(phone)
    print("\n✅ Your session string is:\n")
    print(client.session.save())
