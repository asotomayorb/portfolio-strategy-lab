import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_tiingo_coverage as probe
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


def test_new_equity_with_no_history_still_passes_current_price_coverage(monkeypatch):
    def fake_get_json(path, token):
        if "/intraday/" in path:
            return [{"ticker": "SPCX", "tngoLast": 42.5, "timestamp": "2026-11-09T15:00:00Z"}]
        return []

    monkeypatch.setattr(probe, "_get_json", fake_get_json)
    result = probe.check_equity("SPCX", "test-token", "2024-01-01")
    assert result["coverage_pass"] is True
    assert result["reference_price_available"] is True
    assert result["valid_daily_ohlc_rows"] == 0
    assert result["history_status"] == "no_history_in_requested_window"


def test_equity_without_current_reference_price_fails_coverage(monkeypatch):
    def fake_get_json(path, token):
        if "/intraday/" in path:
            return [{"ticker": "SPCX", "tngoLast": None}]
        return []

    monkeypatch.setattr(probe, "_get_json", fake_get_json)
    result = probe.check_equity("SPCX", "test-token", "2024-01-01")
    assert result["coverage_pass"] is False


def test_new_crypto_pair_with_current_price_does_not_require_history(monkeypatch):
    calls = {"count": 0}

    def fake_get_json(path, token):
        calls["count"] += 1
        if calls["count"] == 1:
            return [{
                "ticker": "btcusd",
                "baseCurrency": "btc",
                "quoteCurrency": "usd",
                "priceData": {"close": 65000, "date": "2026-11-09T15:00:00Z"},
            }]
        return [{"ticker": "btcusd", "priceData": []}]

    monkeypatch.setattr(probe, "_get_json", fake_get_json)
    result = probe.check_crypto("btcusd", "test-token", "2024-01-01")
    assert result["coverage_pass"] is True
    assert result["valid_daily_ohlc_rows"] == 0
    assert result["history_status"] == "no_history_in_requested_window"
