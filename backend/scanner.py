import numpy as np
import pandas as pd
import yfinance as yf


class MarketScannerService:

    def calculate_volatility_and_volume(
        self, price_data: list, window: int = 20
    ):
        if len(price_data) < window:
            return {"error": "Not enough data points to compute metrics."}

        df = pd.DataFrame(price_data)
        df["returns"] = df["close"].pct_change()
        df["volatility"] = (
            df["returns"].rolling(window=window).std() * np.sqrt(252)
        )
        df["avg_volume"] = df["volume"].rolling(window=window).mean()
        df["volume_ratio"] = df["volume"] / df["avg_volume"]

        latest_metrics = df.iloc[-1].to_dict()
        return {
            "current_close": latest_metrics.get("close"),
            "annualized_volatility": latest_metrics.get("volatility"),
            "volume_spike_ratio": latest_metrics.get("volume_ratio"),
        }

    def get_historical_metrics_series(self, price_data: list, window: int = 20):
        if len(price_data) < window:
            return []

        df = pd.DataFrame(price_data)
        df["returns"] = df["close"].pct_change()
        df["volatility"] = (
            df["returns"].rolling(window=window).std() * np.sqrt(252)
        )
        df["avg_volume"] = df["volume"].rolling(window=window).mean()
        df["volume_ratio"] = df["volume"] / df["avg_volume"]

        df = df.dropna(subset=["volatility"])

        history_list = []
        for _, row in df.iterrows():
            history_list.append({
                "date": str(row.get("date", "")),
                "close": float(row["close"]),
                "volatility": (
                    float(row["volatility"])
                    if not pd.isna(row["volatility"])
                    else 0
                ),
                "volume_ratio": (
                    float(row["volume_ratio"])
                    if not pd.isna(row["volume_ratio"])
                    else 0
                ),
            })
        return history_list

    def fetch_yfinance_data(self, symbol: str, period: str = "1mo"):
        """Helper function to cleanly fetch and format historical records."""
        ticker = yf.Ticker(symbol.upper())
        history = ticker.history(period=period)

        if history.empty:
            return []

        return [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            for idx, row in history.iterrows()
        ]

    def run_morning_screener(self, tickers: list, volatility_threshold: float):
        """Processes a target batch list and filters out low volatility assets."""
        screened_alerts = {}

        for symbol in tickers:
            price_data = self.fetch_yfinance_data(symbol, period="1mo")
            if len(price_data) < 20:
                continue

            latest_snapshot = self.calculate_volatility_and_volume(price_data)
            current_vol = latest_snapshot.get("annualized_volatility", 0)

            if current_vol >= volatility_threshold:
                full_timeline = self.get_historical_metrics_series(price_data)
                screened_alerts[symbol.upper()] = {
                    "latest_summary": latest_snapshot,
                    "historical_timeline": full_timeline,
                }

        return screened_alerts

    def detect_volume_anomalies(self, tickers: list, adv_multiplier: float = 1.5):
        """Detects volume spikes that exceed the ADV (Average Daily Volume) multiplier threshold."""
        anomalies = {}

        for symbol in tickers:
            price_data = self.fetch_yfinance_data(symbol, period="1mo")
            if len(price_data) < 20:
                continue

            latest_snapshot = self.calculate_volatility_and_volume(price_data)
            volume_ratio = latest_snapshot.get("volume_spike_ratio", 0)

            if volume_ratio >= adv_multiplier:
                full_timeline = self.get_historical_metrics_series(price_data)
                anomalies[symbol.upper()] = {
                    "volume_ratio": volume_ratio,
                    "current_close": latest_snapshot.get("current_close"),
                    "annualized_volatility": latest_snapshot.get("annualized_volatility"),
                    "threshold": adv_multiplier,
                    "volume_spike_detected": True,
                    "historical_timeline": full_timeline,
                }

        return anomalies
    
    def calculate_atr(self, symbol: str, period: int = 14) -> float:

        """Calculates the 14-day Average True Range for a given ticker. ATR measures average daily price movement — used for stop-loss calculation."""

        ticker = yf.Ticker(symbol.upper())
        history = ticker.history(period="1mo")

        if history.empty or len(history) < period:
            return 0.0

        high = history['High']
        low = history['Low']
        close = history['Close']

        true_ranges = []
        for i in range(1, len(history)):
            tr = max(
                high.iloc[i] - low.iloc[i],
                abs(high.iloc[i] - close.iloc[i - 1]),
                abs(low.iloc[i] - close.iloc[i - 1])
            )
            true_ranges.append(tr)

        atr = sum(true_ranges[-period:]) / period
        return round(atr, 4)


    def calculate_stop_loss(self, current_price: float, atr: float, bias: str) -> float:

        """
        Calculates algorithmic stop-loss based on ATR and directional bias.
        Bullish: stop-loss below current price (2x ATR)
        Bearish: stop-loss above current price (2x ATR)
       
        """

        if bias.lower() == "bullish":
            return float(round(current_price - (2 * atr), 2))
        elif bias.lower() == "bearish":
            return float(round(current_price + (2 * atr), 2))
        else:
            return float(round(current_price - (1.5 * atr), 2))


    def calculate_profit_target(self, current_price: float, atr: float, bias: str) -> float:

        """Calculates profit target based on ATR (3:1 reward-to-risk ratio) """

        if bias.lower() == "bullish":
            return float(round(current_price + (3 * atr), 2))
        elif bias.lower() == "bearish":
            return float(round(current_price - (3 * atr), 2))
        else:
            return float(round(current_price + (2 * atr), 2))
