"""Build the Phase 1 experiment matrix without running it.

This freezes the strategy names/parameters in one auditable artifact.
"""
from pathlib import Path
import yaml

CONFIG = Path(__file__).parents[1] / "config" / "phase1.yaml"

def main():
    cfg = yaml.safe_load(CONFIG.read_text())
    strategies = {
        "B0_buy_hold": "fixed target weights",
        "B1_dca": "fixed target weights + monthly contributions",
        "S1_momentum": f"{cfg['strategies']['momentum']['lookback_months']}m, top {cfg['strategies']['momentum']['top_n']}",
        "S2_value": "eligible comparable assets only",
        "S3_rotation": f"{cfg['strategies']['rotation']['lookback_months']}m, top {cfg['strategies']['rotation']['top_n']}",
        "S4_moving_average": f"{cfg['strategies']['moving_average']['window_days']}d SMA",
        "S5_dynamic_allocation": f"positive return score, cap {cfg['strategies']['dynamic_allocation']['max_weight']}",
        "S6_risk_parity": f"{cfg['strategies']['risk_parity']['window_days']}d window, equal risk contribution",
    }
    print("PHASE 1 FROZEN MATRIX")
    for k,v in strategies.items():
        print(f"- {k}: {v}")

if __name__ == "__main__":
    main()
