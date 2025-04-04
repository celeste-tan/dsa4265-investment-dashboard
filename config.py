from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ESG_API_TOKEN = os.getenv("ESG_API_TOKEN")

DEFAULT_PERIOD = "1y"
