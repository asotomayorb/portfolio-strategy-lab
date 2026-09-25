import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import numpy as np
import pandas as pd

from backtest import simulate
from data_loader import normalize_columns
from metrics import summarize


def test_invalid_ohlc_flagged():
    df = pd.DataFrame({"Date": ["2024-01-01"], "Open": [10], "High": [9], "Low": [8], "Close": [9]})
    out = normalize_columns(df)
    assert out.loc[0, "ohlc_valid"] == False


def test_execution_is_after_decision():
    idx = pd.date_range("2024-01-01", periods=45, freq="B")
    prices = pd.DataFrame({"A": range(100, 145)}, index=idx, dtype=float)
    weights = pd.DataFrame(1.0, index=idx, columns=["A"])
    eq, _, _ = simulate(prices, weights, 1000, 0)
    assert eq.index[0] > idx[0]


def test_no_negative_cash():
    idx = pd.date_range("2024-01-01", periods=100, freq="B")
    prices = pd.DataFrame({"A": 100.0, "B": 100.0}, index=idx)
    weights = pd.DataFrame({"A": 0.8, "B": 0.8}, index=idx)
    eq, _, _ = simulate(prices, weights, 1000, 0)
    assert (eq["cash"] >= -1e-9).all()


def test_metrics_has_core_fields():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    equity = pd.Series(np.linspace(100, 160, len(idx)), index=idx)
    out = summarize(equity)
    for field in ["final_value", "CAGR", "ann_vol", "max_drawdown", "Sharpe", "Sortino", "Calmar"]:
        assert field in out


def test_metrics_recovery_is_not_negative():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    equity = pd.Series([100, 90, 80, 90, 100, 110] + [110] * 18, index=idx)
    out = summarize(equity)
    assert out["longest_recovery_months"] >= 0


def test_target_cash_is_preserved():
    idx = pd.date_range("2024-01-01", periods=70, freq="B")
    prices = pd.DataFrame({"A": 100.0}, index=idx)
    weights = pd.DataFrame({"A": 0.95}, index=idx)
    eq, _, _ = simulate(prices, weights, 1000, 0, commission_bps=0, slippage_bps=0)
    assert eq["cash"].iloc[-1] == pytest.approx(50.0, abs=1e-8)


def test_allocation_csv_maps_btcusd_and_cash(tmp_path):
    sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
    from experiment import load_targets
    path = tmp_path / "portfolio_allocation.csv"
    path.write_text("Ticker,Allocation %\nBTCUSD,10%\nQQQ,85%\ncash,5%\n", encoding="utf-8")
    out = load_targets({}, path)
    assert out["BTC"] == pytest.approx(0.10)
    assert out["QQQ"] == pytest.approx(0.85)
    assert out["CASH"] == pytest.approx(0.05)
