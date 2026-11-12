import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_eodhd_split_adjustment as probe


def test_parse_split_events_supports_fractional_and_reverse_ratios():
    events = probe.parse_split_events([
        {"date": "2024-06-10", "split": "10.000000/1.000000"},
        {"date": "2025-02-03", "split": "1.000000/8.000000"},
        {"date": "2025-03-03", "split": "1.500000/1.000000"},
    ])
    assert events[0]["ratio"] == 10
    assert events[1]["ratio"] == 0.125
    assert events[2]["ratio"] == 1.5


def test_parse_split_events_rejects_invalid_ratio():
    import pytest
    with pytest.raises(probe.ProviderRequestError):
        probe.parse_split_events([{"date": "2024-06-10", "split": "10/0"}])


def test_split_adjustment_only_changes_bars_before_ex_date():
    rows = [
        {"date": "2024-06-07", "open": 1200, "high": 1220, "low": 1180, "close": 1210},
        {"date": "2024-06-10", "open": 121, "high": 123, "low": 119, "close": 122},
    ]
    events = probe.parse_split_events([
        {"date": "2024-06-10", "split": "10.000000/1.000000"}
    ])
    adjusted = probe.apply_split_adjustments(rows, events)
    assert adjusted[0]["close"] == 121
    assert adjusted[0]["high"] == 122
    assert adjusted[0]["split_adjustment_factor"] == 10
    assert adjusted[1]["close"] == 122
    assert adjusted[1]["split_adjustment_factor"] == 1


def test_multiple_and_reverse_splits_accumulate_correctly():
    rows = [
        {"date": "2024-01-01", "open": 800, "high": 880, "low": 720, "close": 840},
    ]
    events = probe.parse_split_events([
        {"date": "2024-02-01", "split": "2/1"},
        {"date": "2024-03-01", "split": "1/2"},
    ])
    adjusted = probe.apply_split_adjustments(rows, events)[0]
    assert adjusted["split_adjustment_factor"] == 1
    assert adjusted["close"] == 840


def test_no_split_events_preserves_raw_ohlc():
    rows = [
        {"date": "2024-01-01", "open": 10, "high": 12, "low": 9, "close": 11}
    ]
    assert probe.apply_split_adjustments(rows, []) == [
        {**rows[0], "split_adjustment_factor": 1.0}
    ]


def test_valid_ohlc_rejects_impossible_rows():
    rows = [
        {"date": "2024-06-07", "open": 10, "high": 12, "low": 9, "close": 11},
        {"date": "2024-06-08", "open": 10, "high": 9, "low": 8, "close": 11},
    ]
    assert len(probe._valid_ohlc_rows(rows)) == 1


def test_compare_symbol_uses_eod_and_splits_endpoints(monkeypatch):
    raw = [
        {"date": "2024-06-07", "open": 1200, "high": 1220, "low": 1180, "close": 1210},
        {"date": "2024-06-10", "open": 121, "high": 123, "low": 119, "close": 122},
    ]
    responses = iter([
        raw,
        [{"date": "2024-06-10", "split": "10/1"}],
    ])
    monkeypatch.setattr(probe, "_get_json", lambda *args, **kwargs: next(responses))
    result = probe.compare_symbol("NVDA.US", "test-token", "2023-01-01", "2026-11-12")
    assert result["data_valid"] is True
    assert result["split_event_count"] == 1
    assert result["rows_adjusted"] == 1
    assert result["split_adjustment_detected"] is True
