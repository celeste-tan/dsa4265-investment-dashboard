import praw
import datetime
import time
import pandas as pd
import re
import os
from openai import OpenAI
from dotenv import load_dotenv


# OpenAI API Setup
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) 

# Reddit API Variables
reddit = praw.Reddit(
    client_id="DigBa8E0LvB9sIKdM54j_A",
    client_secret="yZJtGdsTrS8xSR6QCRe0Xl9Dw7Mj9g",
    user_agent="financial-news-scraper"
)

# === Target Subreddits ===
subreddits = ["stocks", "investing", "finance", "wallstreetbets", "options"]

# === User Input ===
def get_user_inputs():
    tickers_input = input("Enter one or more stock symbols separated by commas (e.g. AAPL, MSFT, TSLA): ")
    ticker_symbols = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]
    days_back = 186
    return ticker_symbols, days_back

# === Scrape Reddit ===
def scrape_reddit(tickers, days_back):
    current_time = time.time()
    time_threshold = current_time - (days_back * 86400)
    all_posts = []

    for subreddit_name in subreddits:
        subreddit = reddit.subreddit(subreddit_name)
        for ticker in tickers:
            print(f"Scraping r/{subreddit_name} for '{ticker}' mentions (Last {days_back} days)...")
            search_results = subreddit.search(ticker, sort="new", time_filter="all")

            for post in search_results:
                if post.created_utc >= time_threshold:
                    post_date = datetime.datetime.utcfromtimestamp(post.created_utc)
                    all_posts.append({
                        "subreddit": subreddit_name,
                        "ticker": ticker,
                        "title": post.title,
                        "url": post.url,
                        "upvotes": post.score,
                        "created_on": post_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "content": post.selftext
                    })
    return pd.DataFrame(all_posts)

# === Text Cleaning ===
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

# === Sentiment Classification ===
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
        return "neutral"

# === Main Pipeline ===
def main():
    tickers, days_back = get_user_inputs()
    print("\nFetching Reddit stock discussions...\n")

    df = scrape_reddit(tickers, days_back)
    if df.empty:
        print("No relevant Reddit posts found.")
        return

    # Filter low engagement
    df = df[df['upvotes'] >= 3]
    df = df[df['title'].notna() & df['title'].str.strip().ne("")]

    # Clean text
    df["title"] = df["title"].apply(clean_text).apply(remove_emoji)

    # Classify sentiment
    df["openai_sentiment"] = df.apply(
        lambda row: get_openai_sentiment(row["title"], row["ticker"]), axis=1
    )

    print("\nSample processed data:")
    print(df[["title", "ticker", "openai_sentiment"]].head(10))

    return df

if __name__ == "__main__":
    cleaned_df = main()
