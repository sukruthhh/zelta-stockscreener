from fastapi import FastAPI
import yfinance as yf

app = FastAPI()

@app.get("/api/v1/test-ticker/{symbol}")
async def test_ticker(symbol: str):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="1d")
    current_price = history['Close'].iloc[-1]
    return {"ticker": symbol, "live_price": float(current_price)}