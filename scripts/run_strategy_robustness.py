"""Robustness comparison for Phase 1 strategies across expanding/common histories."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment import run_phase1


KEYS = ["CAGR", "Sharpe", "Sortino", "Calmar", "max_drawdown", "longest_recovery_months"]


def pareto_front(frame: pd.DataFrame) -> list[str]:
    names = frame["strategy"].tolist()
    front = []
    for i, a in frame.iterrows():
        dominated = False
        for j, b in frame.iterrows():
            if i == j:
                continue
            better_or_equal = (
                b["CAGR"] >= a["CAGR"]
                and b["Sharpe"] >= a["Sharpe"]
                and b["Sortino"] >= a["Sortino"]
                and b["Calmar"] >= a["Calmar"]
                and b["max_drawdown"] >= a["max_drawdown"]
                and b["longest_recovery_months"] <= a["longest_recovery_months"]
            )
            strictly_better = (
                b["CAGR"] > a["CAGR"]
                or b["Sharpe"] > a["Sharpe"]
                or b["Sortino"] > a["Sortino"]
                or b["Calmar"] > a["Calmar"]
                or b["max_drawdown"] > a["max_drawdown"]
                or b["longest_recovery_months"] < a["longest_recovery_months"]
            )
            if better_or_equal and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(names[i])
    return front


def main() -> None:
    expanding = run_phase1(history_mode="expanding")
    common = run_phase1(history_mode="common")
    e = expanding[["strategy"] + KEYS].copy()
    e["history_mode"] = "expanding"
    c = common[["strategy"] + KEYS].copy()
    c["history_mode"] = "common"
    all_rows = pd.concat([e, c], ignore_index=True)
    all_rows = all_rows.sort_values(["history_mode", "strategy"]).reset_index(drop=True)

    # A strategy is considered robustly dominant only if it is on the
    # Pareto frontier in both histories and no other strategy is on the
    # frontier in either history. This deliberately avoids an arbitrary
    # weighted score.
    fronts = {
        "expanding": pareto_front(e.reset_index(drop=True)),
        "common": pareto_front(c.reset_index(drop=True)),
    }
    intersection = sorted(set(fronts["expanding"]) & set(fronts["common"]))
    unique = intersection if len(intersection) == 1 else []

    print("ROBUSTNESS_RESULT")
    print("expanding_front=" + ",".join(fronts["expanding"]))
    print("common_front=" + ",".join(fronts["common"]))
    print("robust_pareto_winner=" + (unique[0] if unique else "NONE"))
    print("DATA")
    print(all_rows.to_csv(index=False))

    out = ROOT / "strategy_robustness_ci.csv"
    all_rows.to_csv(out, index=False)
    (ROOT / "strategy_robustness_summary.txt").write_text(
        "expanding_front=" + ",".join(fronts["expanding"]) + "\n"
        + "common_front=" + ",".join(fronts["common"]) + "\n"
        + "robust_pareto_winner=" + (unique[0] if unique else "NONE") + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
