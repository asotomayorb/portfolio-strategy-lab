"""Deterministic Phase 1 experiment runner."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml
from data_loader import load_csv_folder, close_matrix
from backtest import simulate
from metrics import summarize
from strategies import buy_and_hold, dca, momentum, rotation, moving_average, dynamic_allocation, risk_parity

CONFIG = Path(__file__).parents[1] / "config" / "phase1.yaml"
TICKER_DIR = Path(__file__).parents[1] / "tickers"

def load_config(path=CONFIG):
    return yaml.safe_load(Path(path).read_text())

def load_targets(cfg):
    weights = cfg.get("portfolio", {}).get("target_weights", {})
    result = {str(k).upper(): float(v) for k, v in weights.items()}
    if result:
        total = sum(result.values())
        if total <= 0:
            raise ValueError("portfolio.target_weights must contain positive weights")
        return {k: v / total for k, v in result.items()}
    return {}

def prepare_prices(ticker_dir=TICKER_DIR):
    return close_matrix(load_csv_folder(ticker_dir))

def _signals(prices, targets, cfg):
    return {
        "B0_buy_hold": buy_and_hold(prices, targets),
        "B1_dca": dca(prices, targets),
        "S1_momentum": momentum(prices, cfg["strategies"]["momentum"]["lookback_months"], cfg["strategies"]["momentum"]["top_n"]),
        "S3_rotation": rotation(prices, cfg["strategies"]["rotation"]["lookback_months"], cfg["strategies"]["rotation"]["top_n"]),
        "S4_moving_average": moving_average(prices, cfg["strategies"]["moving_average"]["window_days"]),
        "S5_dynamic_allocation": dynamic_allocation(prices, cfg["strategies"]["dynamic_allocation"]["lookback_months"], cfg["strategies"]["dynamic_allocation"]["max_weight"]),
        "S6_risk_parity": risk_parity(prices, cfg["strategies"]["risk_parity"]["volatility_window_days"]),
    }

def run_phase1(ticker_dir=TICKER_DIR, cfg_path=CONFIG, initial_capital=None, monthly_contribution=None):
    cfg = load_config(cfg_path)
    prices = prepare_prices(ticker_dir)
    targets = load_targets(cfg)
    initial_capital = cfg["portfolio"]["initial_capital"] if initial_capital is None else initial_capital
    monthly_contribution = cfg["portfolio"]["monthly_contribution"] if monthly_contribution is None else monthly_contribution
    signals = _signals(prices, targets, cfg)
    rows = []
    for name, sig in signals.items():
        if name in {"B0_buy_hold", "B1_dca"} and not targets:
            continue
        invest = name != "B0_buy_hold"
        rebalance = name != "B0_buy_hold"
        eq, turnover, trades = simulate(prices, sig, initial_capital,
            monthly_contribution if invest else 0.0,
            cfg["costs"]["commission_bps"], cfg["costs"]["slippage_bps"],
            invest_contributions=invest, rebalance=rebalance)
        if eq.empty:
            continue
        m = summarize(eq["equity"], turnover=turnover, trades=trades)
        m.update({"strategy": name, "dataset_version": cfg["dataset_version"], "config_version": cfg["config_version"]})
        rows.append(m)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", default=str(TICKER_DIR))
    p.add_argument("--output", default=None)
    a = p.parse_args()
    result = run_phase1(a.tickers)
    print(result.to_string(index=False))
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(a.output, index=False)
