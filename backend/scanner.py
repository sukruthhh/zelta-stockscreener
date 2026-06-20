import numpy as np
import pandas as pd


class MarketScannerService:

    def calculate_volatility_and_volume(
        self, price_data: list, window: int = 20
    ):
        """price_data is a list of dicts with historical stock data:

        [{'close': 15.20, 'volume': 500000}, ...]
        """
        if len(price_data) < window:
            return {"error": "Not enough data points to compute metrics."}

        # 1. Load into a Pandas DataFrame
        df = pd.DataFrame(price_data)

        # 2. Calculate Daily Returns
        df["returns"] = df["close"].pct_change()

        # 3. Calculate Annualized Historical Volatility (252 trading days/year)
        df["volatility"] = (
            df["returns"].rolling(window=window).std() * np.sqrt(252)
        )

        # 4. Calculate Volume Moving Average and Spike Ratio
        df["avg_volume"] = df["volume"].rolling(window=window).mean()
        df["volume_ratio"] = df["volume"] / df["avg_volume"]

        # Extract the latest calculated row
        latest_metrics = df.iloc[-1].to_dict()

        return {
            "current_close": latest_metrics.get("close"),
            "annualized_volatility": latest_metrics.get("volatility"),
            "volume_spike_ratio": latest_metrics.get("volume_ratio"),
        }