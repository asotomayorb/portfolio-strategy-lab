"""Run the frozen Phase 1 experiment and write a reproducible CSV report."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment import run_phase1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/phase1_results.csv")
    args = parser.parse_args()

    result = run_phase1()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(result.to_string(index=False))
    print(f"\nWrote {output}")


if __name__ == "__main__":
    main()
