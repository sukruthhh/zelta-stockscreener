from fastapi import FastAPI
import yfinance as yf

from news_harvester import fetch_news
# Import your newly created service from scanner.py
from scanner import MarketScannerService
from vector_pipeline import process_ticker

app = FastAPI()
# Initialize the scanner service engine
scanner_service = MarketScannerService()


@app.get("/api/v1/test-ticker/{symbol}")
async def test_ticker(symbol: str):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="1d")
    current_price = history["Close"].iloc[-1]
    return {"ticker": symbol, "live_price": float(current_price)}


@app.post("/api/v1/harvest/{ticker}")
async def harvest_news(ticker: str):
    articles = fetch_news(ticker.upper())
    if not articles:
        return {"status": "no articles found", "ticker": ticker}

    process_ticker(ticker.upper(), articles)
    return {
        "status": "complete",
        "ticker": ticker.upper(),
        "articles_processed": len(articles),
    }


# NEW ROUTE: Volatility & Volume Scanner Endpoint
@app.get("/api/v1/scan/{symbol}")
async def scan_ticker(symbol: str):
    # 1. Fetch enough historical days to calculate a rolling 20-day window
    ticker = yf.Ticker(symbol.upper())
    history = ticker.history(period="1mo")  # Fetches ~20-22 trading days

    if history.empty or len(history) < 20:
        return {
            "error": f"Not enough historical data found for symbol {symbol}."
        }

    # 2. Transform the yfinance DataFrame into the list of dicts our service expects
    price_data = []
    for index, row in history.iterrows():
        price_data.append({"close": float(row["Close"]), "volume": int(row["Volume"])})

    # 3. Run your mathematical scanner engine
    metrics = scanner_service.calculate_volatility_and_volume(
        price_data, window=20
    )

    return {"ticker": symbol.upper(), "metrics": metrics}