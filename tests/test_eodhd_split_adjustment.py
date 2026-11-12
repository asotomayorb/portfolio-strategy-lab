import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_eodhd_split_adjustment as probe


def _rows():
    return [
        {"date": "2024-06-07", "open": 1200, "high": 1220, "low": 1180, "close": 1210},
        {"date": "2024-06-10", "open": 121, "high": 123, "low": 119, "close": 122},
    ]


def test_valid_rows_rejects_impossible_ohlc():
    rows = _rows() + [
        {"date": "2024-06-11", "open": 100, "high": 90, "low": 80, "close": 95}
    ]
    assert len(probe._valid_rows(rows)) == 2


def test_compare_reports_split_adjustment_and_date_alignment(monkeypatch):
    raw = _rows()
    adjusted = [
        {"date": "2024-06-07", "open": 120, "high": 122, "low": 118, "close": 121},
        {"date": "2024-06-10", "open": 121, "high": 123, "low": 119, "close": 122},
    ]
    responses = iter([raw, adjusted])
    monkeypatch.setattr(probe, "_get_json", lambda *args, **kwargs: next(responses))
    result = probe.compare_symbol("NVDA.US", "test-token", "2023-01-01", "2026-11-12")
    assert result["data_valid"] is True
    assert result["overlapping_dates"] == 2
    assert result["rows_with_split_adjustment"] == 1
    assert result["split_adjustment_detected"] is True


def test_no_overlap_is_not_valid(monkeypatch):
    responses = iter([
        [{"date": "2024-06-07", "open": 10, "high": 12, "low": 9, "close": 11}],
        [{"date": "2024-06-10", "open": 10, "high": 12, "low": 9, "close": 11}],
    ])
    monkeypatch.setattr(probe, "_get_json", lambda *args, **kwargs: next(responses))
    result = probe.compare_symbol("QQQ.US", "test-token", "2023-01-01", "2026-11-12")
    assert result["data_valid"] is False


def test_provider_errors_are_sanitized(monkeypatch):
    def fail(*args, **kwargs):
        raise probe.ProviderRequestError("HTTP 403")
    monkeypatch.setattr(probe, "_get_json", fail)
    try:
        probe.compare_symbol("NVDA.US", "very-secret-token", "2023-01-01", "2026-11-12")
    except probe.ProviderRequestError as exc:
        assert str(exc) == "HTTP 403"
        assert "very-secret-token" not in str(exc)
    else:
        raise AssertionError("expected provider error")
