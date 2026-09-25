import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import numpy as np
import pandas as pd

from backtest import simulate
from data_loader import normalize_columns
from metrics import summarize
from strategies import momentum, rotation


def test_invalid_ohlc_flagged():
    df = pd.DataFrame({"Date": ["2024-01-01"], "Open": [10], "High": [9], "Low": [8], "Close": [9]})
    out = normalize_columns(df)
    assert out.loc[0, "ohlc_valid"] == False


def test_btc_thousands_separators_are_numeric():
    df = pd.DataFrame({
        "Date": ["30/09/2020"],
        "Open": ['"10,843.40"'],
        "High": ['"10,847.70"'],
        "Low": ['"10,667.60"'],
        "Close": ['"10,776.10"'],
    })
    out = normalize_columns(df)
    assert out.loc[0, "Close"] == pytest.approx(10776.10)
    assert bool(out.loc[0, "ohlc_valid"]) is True


def test_close_matrix_preserves_date_indexed_validity_mask():
    from data_loader import AssetData, close_matrix

    frame = pd.DataFrame({
        "Date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "Open": [10.0, 10.0],
        "High": [11.0, 9.0],
        "Low": [9.0, 8.0],
        "Close": [10.5, 8.5],
        "ohlc_valid": [True, False],
    })
    out = close_matrix({"A": AssetData("A", frame)})
    assert out.loc[pd.Timestamp("2024-01-02"), "A"] == pytest.approx(10.5)
    assert pd.isna(out.loc[pd.Timestamp("2024-01-03"), "A"])


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
    for field in ["final_value", "CAGR", "ann_vol", "max_drawdown", "Sharpe", "Sortino", "Calmar", "worst_calendar_year"]:
        assert field in out


def test_metrics_are_not_distorted_by_contributions():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    equity = pd.Series(1100.0 + 100.0 * np.arange(len(idx)), index=idx)
    flows = pd.Series(100.0, index=idx)
    out = summarize(equity, external_cashflows=flows, initial_capital=1000.0)
    assert abs(out["CAGR"]) < 1e-10
    assert abs(out["ann_vol"]) < 1e-10


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


def test_buy_and_hold_repository_simulation_has_history():
    from experiment import load_config, load_targets, prepare_prices
    from strategies import buy_and_hold
    cfg = load_config()
    targets = {k: v for k, v in load_targets(cfg).items() if k != "CASH"}
    prices = prepare_prices()
    signal = buy_and_hold(prices, targets)
    eq, _, _ = simulate(prices, signal, 100000, 0)
    assert not eq.empty, (
        f"B0 empty: prices={prices.index.min()}..{prices.index.max()}, "
        f"rows={len(prices)}, cols={list(prices.columns)}, "
        f"signal_rows={len(signal)}, target_assets={list(targets)}"
    )


# Repository-level Phase 1 coverage is intentionally exercised in CI.

def test_phase1_smoke_with_repository_data():
    from experiment import run_phase1, load_config, load_targets, allocation_metadata
    cfg = load_config()
    targets = load_targets(cfg)
    assert targets["CASH"] == pytest.approx(0.05)
    assert sum(targets.values()) == pytest.approx(1.0)
    result = run_phase1()
    assert not result.empty
    assert set(result["strategy"]) == set(["B0_buy_hold", "B1_dca", "S1_momentum", "S3_rotation", "S4_moving_average", "S5_dynamic_allocation", "S6_risk_parity"])
    assert set(["B0_buy_hold", "B1_dca", "S1_momentum", "S3_rotation",
                "S4_moving_average", "S5_dynamic_allocation", "S6_risk_parity"]).issubset(
        set(result["strategy"])
    )
    assert np.allclose(result["allocation_total"].to_numpy(), 1.0, atol=1e-10)
    assert np.allclose(result["cash_target"].to_numpy(), 0.05, atol=1e-10)


def test_rotation_can_move_to_cash_when_all_returns_are_non_positive():
    idx = pd.date_range("2020-01-01", periods=30, freq="ME")
    prices = pd.DataFrame({"A": 100.0, "B": 100.0}, index=idx)
    prices.loc[idx[-1], ["A", "B"]] = 90.0
    m = momentum(prices, lookback_months=12, top_n=1)
    r = rotation(prices, lookback_months=12, top_n=1)
    assert r.iloc[-1].sum() == pytest.approx(0.0)
    assert m.iloc[-1].sum() == pytest.approx(1.0)


def test_phase1_tactical_signals_respect_cash_reserve():
    from experiment import _signals, load_config

    idx = pd.date_range("2024-01-01", periods=40, freq="B")
    prices = pd.DataFrame(
        {ticker: np.linspace(100.0, 140.0, len(idx)) for ticker in ["A", "B", "C"]},
        index=idx,
    )
    targets = {"A": 0.50, "B": 0.25, "C": 0.20, "CASH": 0.05}
    signals = _signals(prices, targets, load_config())
    for name, signal in signals.items():
        row_sums = signal.sum(axis=1)
        if name in {"B0_buy_hold", "B1_dca"}:
            assert np.nanmax(row_sums.to_numpy()) <= 0.95 + 1e-10
        else:
            assert np.nanmax(row_sums.to_numpy()) <= 0.95 + 1e-10
