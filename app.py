from pathlib import Path
import sys
import streamlit as st
import pandas as pd

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from data_loader import load_csv_folder, close_matrix
from history import common_history_start
from experiment import run_phase1, load_config, load_targets, allocation_metadata

TICKER_DIR = ROOT / "tickers"

st.set_page_config(page_title="Portfolio Strategy Lab", layout="wide")
st.title("Portfolio Strategy Lab")
st.caption("Phase 1: reproducible strategy-family comparison. Data is read directly from GitHub /tickers/*.csv.")

try:
    assets = load_csv_folder(TICKER_DIR)
    prices = close_matrix(assets)
    cfg = load_config()
except Exception as exc:
    st.error(f"No se pudo leer la carpeta tickers: {exc}")
    st.stop()

st.success(f"Dataset leído: {len(assets)} tickers, {len(prices):,} fechas.")

try:
    common_start = common_history_start(prices)
    st.info(f"Historia común de todo el universo: {common_start.date()}")
except Exception as exc:
    st.warning(f"No se pudo determinar la historia común: {exc}")

quality = []
for ticker, asset in assets.items():
    frame = asset.frame
    quality.append({
        "Ticker": ticker,
        "Inicio": frame["Date"].min().date(),
        "Fin": frame["Date"].max().date(),
        "Filas": len(frame),
        "OHLC inválidas": int((~frame["ohlc_valid"]).sum()),
    })

st.subheader("Validación")
st.dataframe(pd.DataFrame(quality), use_container_width=True, hide_index=True)

try:
    alloc = load_targets(cfg)
    missing = sorted(set(alloc) - {"CASH"} - set(assets))
    if missing:
        raise ValueError("Allocation contiene tickers sin CSV en /tickers: " + ", ".join(missing))
    meta = allocation_metadata(cfg)
    st.subheader("Portfolio allocation")
    st.dataframe(
        pd.DataFrame([
            {"Ticker": k, "Allocation %": round(v * 100, 2)}
            for k, v in alloc.items()
        ]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        f"Archivo: {meta['allocation_file']} · versión por contenido: "
        f"{meta['allocation_sha256']} · efectivo objetivo: {meta['cash_target']:.1%}"
    )
except Exception as exc:
    st.error(f"Allocation inválido: {exc}")
    st.stop()

if st.button("Ejecutar Phase 1", type="primary"):
    with st.spinner("Ejecutando simulaciones..."):
        result = run_phase1(TICKER_DIR)
    st.subheader("Resultados")
    if result.empty:
        st.warning("No se generaron resultados con el dataset/configuración actual.")
    else:
        display = result.copy()
        for col in ["CAGR", "ann_vol", "max_drawdown", "Sharpe", "Sortino", "Calmar"]:
            if col in display:
                display[col] = display[col].astype(float).round(4)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.subheader("Comparación visual")
        if "CAGR" in result.columns and "max_drawdown" in result.columns:
            chart = result.set_index("strategy")[["CAGR", "max_drawdown"]]
            st.bar_chart(chart)
        st.download_button(
            "Descargar resultados CSV",
            result.to_csv(index=False).encode("utf-8"),
            file_name="phase1_results.csv",
            mime="text/csv",
        )
