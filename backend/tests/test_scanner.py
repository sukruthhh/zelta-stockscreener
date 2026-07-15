import numpy as np

from scanner import MarketScannerService


def test_risk_prices_are_native_python_floats():
    scanner = MarketScannerService()
    current_price = np.float64(133.75999450683594)
    atr = np.float64(7.2196)

    stop_loss = scanner.calculate_stop_loss(current_price, atr, "bearish")
    profit_target = scanner.calculate_profit_target(current_price, atr, "bearish")

    assert type(stop_loss) is float
    assert type(profit_target) is float
    assert stop_loss == 148.20
    assert profit_target == 112.10
