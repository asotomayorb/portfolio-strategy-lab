import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_eodhd_coverage as probe
from validate_eodhd_coverage import (
    ProviderRequestError,
    _valid_ohlc_rows,
    check_symbol,
    load_symbols,
    to_eodhd_symbol,
)


def test_symbol_mapping_handles_us_equities_crypto_and_explicit_symbols():
    assert to_eodhd_symbol("QQQ") == "QQQ.US"
    assert to_eodhd_symbol("BTCUSD") == "BTC-USD.CC"
    assert to_eodhd_symbol("BTC-USD.CC") == "BTC-USD.CC"
    assert to_eodhd_symbol("EURUSD.FOREX") == "EURUSD.FOREX"
    assert to_eodhd_symbol("SPCX.US") == "SPCX.US"


def test_portfolio_symbols_are_loaded_from_allocation_file():
    symbols = load_symbols()
    assert symbols == [
        "VT.US", "SMH.US", "BTC-USD.CC", "INDA.US", "MSFT.US",
        "NVDA.US", "AVGO.US", "GLD.US", "URA.US", "XLE.US",
        "VHT.US", "PLTR.US", "QQQ.US",
    ]


def test_ohlc_validation_rejects_malformed_or_impossible_rows():
    rows = [
        {"date": "2026-11-10", "open": 10, "high": 12, "low": 9, "close": 11},
        {"date": "2026-11-11", "open": 10, "high": 9, "low": 8, "close": 11},
        {"date": "bad-date", "open": 10, "high": 12, "low": 9, "close": 11},
        {"date": "2026-11-12", "open": 0, "high": 12, "low": 9, "close": 11},
    ]
    assert len(_valid_ohlc_rows(rows)) == 1


def test_new_listing_with_short_history_passes_coverage(monkeypatch):
    monkeypatch.setattr(
        probe,
        "_get_json",
        lambda symbol, token, start_date: [
            {
                "date": "2026-11-10",
                "open": 40,
                "high": 43,
                "low": 39,
                "close": 42,
                "adjusted_close": 42,
            }
        ],
    )
    result = check_symbol("SPCX.US", "test-token", "2023-01-01")
    assert result["coverage_pass"] is True
    assert result["valid_daily_ohlc_rows"] == 1
    assert result["latest_bar_date"] == "2026-11-10"


def test_new_listing_with_no_history_is_reported_without_fake_rows(monkeypatch):
    monkeypatch.setattr(probe, "_get_json", lambda *args: [])
    result = check_symbol("SPCX.US", "test-token", "2023-01-01")
    assert result["coverage_pass"] is False
    assert result["valid_daily_ohlc_rows"] == 0
    assert result["latest_bar_date"] is None


def test_adjusted_close_is_counted_but_not_used_as_ohlc(monkeypatch):
    monkeypatch.setattr(
        probe,
        "_get_json",
        lambda *args: [
            {
                "date": "2026-11-10",
                "open": 100,
                "high": 105,
                "low": 98,
                "close": 102,
                "adjusted_close": 95,
            }
        ],
    )
    result = check_symbol("QQQ.US", "test-token", "2023-01-01")
    assert result["coverage_pass"] is True
    assert result["adjusted_close_rows"] == 1
    assert result["ohlc_adjustment"].startswith("raw OHLC")


def test_provider_http_error_is_sanitized(monkeypatch):
    def fail(*args, **kwargs):
        raise ProviderRequestError("HTTP 401")

    monkeypatch.setattr(probe, "_get_json", fail)
    result = check_symbol("QQQ.US", "secret-token", "2023-01-01")
    assert result["coverage_pass"] is False
    assert result["error"] == "HTTP 401"
    assert "secret-token" not in str(result)


def test_request_errors_do_not_leak_query_token(monkeypatch):
    from urllib.error import HTTPError
    import pytest

    def fail(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", hdrs=None, fp=None)

    monkeypatch.setattr(probe, "urlopen", fail)
    with pytest.raises(ProviderRequestError) as exc:
        probe._get_json("QQQ.US", "very-secret-token", "2023-01-01")
    assert str(exc.value) == "HTTP 401"
    assert "very-secret-token" not in str(exc.value)
