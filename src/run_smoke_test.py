"""Small deterministic smoke test; no strategy performance study."""
from __future__ import annotations
import pandas as pd
from strategies import buy_and_hold, dca

def main():
    idx = pd.date_range("2020-01-02", periods=400, freq="B")
    prices = pd.DataFrame({
        "A": 100 * (1.001 ** pd.Series(range(len(idx)), index=idx)),
        "B": 100 * (1.0005 ** pd.Series(range(len(idx)), index=idx)),
    }, index=idx)
    w = {"A": .6, "B": .4}
    for fn in (buy_and_hold, dca):
        s = fn(prices, w)
        assert abs(s.iloc[0].sum() - 1) < 1e-12
    print("SMOKE TEST OK")

if __name__ == "__main__":
    main()
