import praw
import datetime
import time
import re
import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

reddit = praw.Reddit(
    client_id="DigBa8E0LvB9sIKdM54j_A",
    client_secret="yZJtGdsTrS8xSR6QCRe0Xl9Dw7Mj9g",
    user_agent="financial-news-scraper"
)

subreddits = ["stocks", "investing", "finance", "wallstreetbets", "options"]

def clean_text(text):
    if isinstance(text, str):
        text = re.sub(r'@[A-Za-z0-9]+', '', text)
        text = re.sub(r'#', '', text)
        text = re.sub(r'RT[\s]+', '', text)
        text = re.sub(r'https?:\/\/\S+', '', text)
        text = re.sub(r':', '', text)
        return text.strip()
    return text

def remove_emoji(text):
    if isinstance(text, str):
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002500-\U00002BEF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001f926-\U0001f937"
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
    return text

def get_openai_sentiment(text, ticker):
    prompt = (
        f"You are a financial sentiment analysis assistant. "
        f"Analyze the sentiment of the following Reddit post title toward the stock '{ticker}'. "
        f"Respond with one word only: Positive, Neutral, or Negative.\n\n"
        f"Title: \"{text}\""
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Neutral"

def get_reddit_sentiment(ticker, days_back=186):
    print(f"\nFetching Reddit stock discussions for {ticker}...\n")

    current_time = time.time()
    time_threshold = current_time - (days_back * 86400)
    posts = []

    for subreddit_name in subreddits:
        print(f"Scraping r/{subreddit_name} for '{ticker}' mentions (Last {days_back} days)...")
        subreddit = reddit.subreddit(subreddit_name)
        results = subreddit.search(ticker, sort="new", time_filter="all")

        for post in results:
            if post.created_utc >= time_threshold:
                title = clean_text(remove_emoji(post.title))
                if title and post.score >= 3:
                    posts.append({
                        "title": title,
                        "upvotes": post.score
                    })

    if not posts:
        print("No relevant posts found.\n")
        return f"No notable Reddit discussions found for {ticker} in the last {days_back} days."

    print(f"\nClassifying {len(posts)} posts using OpenAI...\n")
    sentiments = [get_openai_sentiment(post["title"], ticker) for post in posts]
    sentiment_counts = pd.Series(sentiments).value_counts()

    summary = ", ".join(f"{k}: {v}" for k, v in sentiment_counts.items())
    print(f"Done analyzing Reddit sentiment for {ticker}.")
    return f"Reddit sentiment for {ticker} is distributed as follows — {summary}."