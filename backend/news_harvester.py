from datetime import datetime, timedelta
import os
import requests
from config import get_settings

# 1. Your original partner logic MUST be present in the file:
def fetch_news(ticker: str):
    """Hits the live Finnhub API endpoint to pull company news for a given ticker."""
    settings = get_settings()
    api_key = settings.finnhub_api_key

    if not api_key:
        print("ERROR: FINNHUB_API_KEY environment variable is missing!")
        return []

    # 📅 Dynamically calculate date windows (from 7 days ago until today)
    today = datetime.now().strftime("%Y-%m-%d")
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # The official Finnhub REST URL format
    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": ticker.upper(),
        "from": one_week_ago,
        "to": today,
        "token": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=settings.news_timeout_seconds)
        if response.status_code == 200:
            return response.json()  # Returns the list of news articles
        else:
            print(
                f"Finnhub API Error: {response.status_code} - {response.text}"
            )
            return []
    except Exception as e:
        print(f"Failed to fetch from Finnhub: {str(e)}")
        return []


# 2. The orchestrator wrapper that main.py calls:
def harvest_and_pipeline_news(ticker: str):
    """Orchestrates news fetching and vector embedding pipeline execution for a given symbol."""
    symbol_upper = ticker.upper()
    
    # This calls the function directly above it in the same file
    articles = fetch_news(symbol_upper)

    if not articles:
        return {"status": "no articles found", "ticker": symbol_upper}

    # Delayed import locally to avoid any potential circular dependencies
    from vector_pipeline import process_ticker

    process_ticker(symbol_upper, articles)

    return {
        "status": "complete",
        "ticker": symbol_upper,
        "articles_processed": len(articles)
    }
