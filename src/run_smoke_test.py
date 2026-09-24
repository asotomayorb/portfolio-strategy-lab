"""Deterministic engine smoke tests; no performance study."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd
from backtest import simulate
from strategies import buy_and_hold, momentum, moving_average

def main():
    idx = pd.date_range("2020-01-02", periods=500, freq="B")
    prices = pd.DataFrame({
        "A": 100 * (1.001 ** pd.Series(range(len(idx)), index=idx)),
        "B": 100 * (1.0005 ** pd.Series(range(len(idx)), index=idx)),
    })
    weights = {"A": .6, "B": .4}
    sig = buy_and_hold(prices, weights)
    eq, turnover, trades = simulate(prices, sig, 100000, 1000)
    assert len(eq) > 0 and (eq["cash"] >= 0).all()
    assert abs(sig.iloc[0].sum() - 1) < 1e-12
    assert momentum(prices).shape == prices.shape
    assert moving_average(prices).shape == prices.shape
    print("SMOKE TEST OK", {"rows": len(eq), "final": round(float(eq.equity.iloc[-1]), 2)})

if __name__ == "__main__":
    main()
