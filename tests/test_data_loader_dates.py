import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from data_loader import normalize_columns

def test_iso_dates_are_not_dayfirst_swapped():
    df = pd.DataFrame({
        "Date": ["2026-08-12", "2026-09-24"],
        "Open": [100, 101], "High": [102, 103],
        "Low": [99, 100], "Close": [101, 102],
    })
    out = normalize_columns(df)
    assert out["Date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-08-12", "2026-09-24"]

def test_legacy_day_month_year_dates_remain_supported():
    df = pd.DataFrame({
        "Date": ["12/08/2026", "24/09/2026"],
        "Open": [100, 101], "High": [102, 103],
        "Low": [99, 100], "Close": [101, 102],
    })
    out = normalize_columns(df)
    assert out["Date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-08-12", "2026-09-24"]
