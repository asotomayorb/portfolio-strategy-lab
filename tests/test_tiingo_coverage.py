import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_tiingo_coverage import _first_record, _positive, _valid_ohlc_rows, load_market_symbols


def test_first_record_handles_list_and_dict():
    assert _first_record([{"ticker": "QQQ"}]) == {"ticker": "QQQ"}
    assert _first_record({"ticker": "QQQ"}) == {"ticker": "QQQ"}
    assert _first_record([]) == {}


def test_positive_rejects_missing_or_invalid_prices():
    assert _positive(100.25)
    assert not _positive(None)
    assert not _positive("not-a-price")
    assert not _positive(0)


def test_valid_ohlc_rows_accepts_daily_list_and_crypto_price_data():
    rows = [
        {"open": 10, "high": 12, "low": 9, "close": 11},
        {"open": 10, "high": 9, "low": 8, "close": 11},
        {"open": 0, "high": 12, "low": 9, "close": 11},
    ]
    assert _valid_ohlc_rows(rows) == 1
    assert _valid_ohlc_rows({"priceData": rows}) == 1
    assert _valid_ohlc_rows(rows[0]) == 1


def test_portfolio_symbols_are_loaded_from_allocation_file():
    equities, crypto_pair = load_market_symbols()
    assert equities == [
        "VT", "SMH", "INDA", "MSFT", "NVDA", "AVGO",
        "GLD", "URA", "XLE", "VHT", "PLTR", "QQQ",
    ]
    assert crypto_pair == "btcusd"
