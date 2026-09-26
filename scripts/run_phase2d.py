"""Phase 2D: run the validated Phase 2A engine with only the cash floor changed to 0%."""
# Execution marker: keep the frozen Phase 2D logic unchanged while allowing a push-triggered run.
from pathlib import Path
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "run_phase2a.py"
OUTPUT = ROOT / "reports" / "phase2d_cash_floor_results.csv"

def main():
    src = SOURCE.read_text(encoding="utf-8")
    old = "floor=0.05*equity"
    if src.count(old) != 1:
        raise RuntimeError("Phase 2A source did not match the frozen cash-floor expression exactly.")
    patched = src.replace(old, "floor=0.0*equity")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "phase2a_floor0.py"
        p.write_text(patched, encoding="utf-8")
        sys.argv = ["phase2a_floor0.py", "--output", str(OUTPUT)]
        runpy.run_path(str(p), run_name="__main__")
    print(f"Wrote {OUTPUT}")

if __name__ == "__main__":
    main()
