# === reddit_headlines.py ===
"""
Scrapes Reddit posts related to a given stock ticker from multiple subreddits,
and classifies sentiment using OpenAI.
"""
import os
import re
import time
import openai
import pandas as pd
import praw
from dotenv import load_dotenv

load_dotenv()

# === Setup OpenAI and Reddit API clients ===
openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.ChatCompletion.create(api_key=openai_api_key)

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="financial-news-scraper"
)

# List of relevant financial subreddits
subreddits = ["stocks", "investing", "finance", "wallstreetbets", "options"]

def clean_text(text):
    """Remove usernames, links, hashtags, and formatting artifacts."""
    if not isinstance(text, str):
        return text
    text = re.sub(r'@[A-Za-z0-9_]+', '', text)
    text = re.sub(r'#', '', text)
    text = re.sub(r'RT[\s]+', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r':', '', text)
    return text.strip()

def remove_emoji(text):
    """Remove emojis using Unicode range matching."""
    if not isinstance(text, str):
        return text
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002500-\U00002BEF"  # CJK
        u"\U00002702-\U000027B0"  # Dingbats
        u"\U000024C2-\U0001F251"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"
        u"\u3030"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r"", text)

def get_openai_sentiment(text, ticker):
    """Use OpenAI to classify sentiment as Positive, Neutral, or Negative."""
    prompt = (
        f"You are a financial sentiment analysis assistant. "
        f"Classify the sentiment of the following Reddit title about '{ticker}':\n"
        f"Title: \"{text}\"\n"
        f"Respond with one word only: Positive, Neutral, or Negative."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Neutral"

def get_reddit_sentiment(ticker, days_back=186):
    """Scrape Reddit for ticker mentions and summarize sentiment."""
    print(f"\nFetching Reddit stock discussions for {ticker}...\n")
    current_time = time.time()
    time_threshold = current_time - (days_back * 86400)
    posts = []

    for subreddit_name in subreddits:
        print(f"Scraping r/{subreddit_name} for '{ticker}' mentions...")
        subreddit = reddit.subreddit(subreddit_name)
        results = subreddit.search(ticker, sort="new", time_filter="all")

        for post in results:
            if post.created_utc >= time_threshold and post.score >= 3:
                title = clean_text(remove_emoji(post.title))
                posts.append({"title": title, "upvotes": post.score})

    if not posts:
        return f"No notable Reddit discussions found for {ticker} in the last {days_back} days."

    print(f"\nClassifying {len(posts)} posts using OpenAI...\n")
    sentiments = [get_openai_sentiment(post["title"], ticker) for post in posts]
    sentiment_counts = pd.Series(sentiments).value_counts()

    summary = ", ".join(f"{k}: {v}" for k, v in sentiment_counts.items())
    print(f"Done analyzing Reddit sentiment for {ticker}.")
    return f"Reddit sentiment for {ticker} — {summary}."
