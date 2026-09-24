import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import pandas as pd
from data_loader import normalize_columns
from backtest import simulate

def test_invalid_ohlc_flagged():
    df = pd.DataFrame({"Date":["2024-01-01"],"Open":[10],"High":[9],"Low":[8],"Close":[9]})
    out = normalize_columns(df)
    assert out.loc[0,"ohlc_valid"] is False

def test_execution_is_after_decision():
    idx = pd.date_range("2024-01-01", periods=45, freq="B")
    prices = pd.DataFrame({"A": range(100,145)}, index=idx, dtype=float)
    weights = pd.DataFrame(1.0, index=idx, columns=["A"])
    eq, _, _ = simulate(prices, weights, 1000, 0)
    assert eq.index[0] > idx[0]

def test_no_negative_cash():
    idx = pd.date_range("2024-01-01", periods=100, freq="B")
    prices = pd.DataFrame({"A":100.0,"B":100.0}, index=idx)
    weights = pd.DataFrame({"A":0.8,"B":0.8}, index=idx)
    eq, _, _ = simulate(prices, weights, 1000, 0)
    assert (eq["cash"] >= -1e-9).all()
