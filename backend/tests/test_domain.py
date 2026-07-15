import pytest

from domain import morning_screener_cache_key, normalize_ticker, parse_assessment


@pytest.mark.parametrize(
    ("value", "expected"),
    [(" aapl ", "AAPL"), ("brk.b", "BRK.B"), ("fngu", "FNGU")],
)
def test_normalize_ticker(value, expected):
    assert normalize_ticker(value) == expected


@pytest.mark.parametrize("value", ["", "AAPL!", "TOO-LONG-TICKER", "../AAPL"])
def test_normalize_ticker_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        normalize_ticker(value)


def test_screener_cache_key_isolated_by_inputs():
    assert morning_screener_cache_key(["MSFT", "AAPL"], 1.5) == "screener:morning:AAPL,MSFT:1.5"
    assert morning_screener_cache_key(["AAPL"], 1.5) != morning_screener_cache_key(["AAPL"], 2)


@pytest.mark.parametrize("assessment", ["Bullish", "Neutral", "Bearish"])
def test_parse_assessment_accepts_all_supported_results(assessment):
    parsed_assessment, payload = parse_assessment(f'{{"final_bias":"{assessment}"}}')
    assert parsed_assessment == assessment.lower()
    assert payload["final_bias"] == assessment


def test_parse_assessment_rejects_unstructured_model_output():
    with pytest.raises(ValueError):
        parse_assessment("Looks bullish to me")

