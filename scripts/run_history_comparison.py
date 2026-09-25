"""Run common-history vs expanding-universe Phase 1 comparisons."""
from pathlib import Path
import argparse
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment import run_phase1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/phase1_history_comparison.csv")
    args = parser.parse_args()

    expanding = run_phase1(history_mode="expanding")
    common = run_phase1(history_mode="common")
    result = pd.concat([expanding, common], ignore_index=True)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(result.to_string(index=False))
    print(f"\nWrote {output}")


if __name__ == "__main__":
    main()
