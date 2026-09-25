from pathlib import Path
import pandas as pd
from src.data_loader import load_csv_folder, close_matrix

def test_csv_folder_loader(tmp_path):
    p = tmp_path / "QQQ.csv"
    p.write_text(
        "QQQ,,,,,\n"
        "Date,Open,High,Low,Close,Volume\n"
        "03/01/2000,96.19,96.19,90.81,94.81,29803600\n"
        "04/01/2000,92,93.49,88.01,88.01,26502200\n",
        encoding="utf-8",
    )
    assets = load_csv_folder(tmp_path)
    assert list(assets) == ["QQQ"]
    assert len(assets["QQQ"].frame) == 2
    prices = close_matrix(assets)
    assert prices.loc[pd.Timestamp("2000-01-03"), "QQQ"] == 94.81

def test_invalid_ohlc_is_flagged(tmp_path):
    p = tmp_path / "BTC.csv"
    p.write_text(
        "BTCUSD,,,,,\n"
        "Date,Open,High,Low,Close,Volume\n"
        "18/07/2010,0,0.1,0.1,0.1,0.08K\n",
        encoding="utf-8",
    )
    assets = load_csv_folder(tmp_path)
    assert not bool(assets["BTC"].frame.loc[0, "ohlc_valid"])
