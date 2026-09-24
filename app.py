import sys
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from data_loader import load_workbook, close_matrix
from experiment import run_phase1, load_targets

st.set_page_config(page_title="Portfolio Strategy Lab", layout="wide")
st.title("Portfolio Strategy Lab")
st.caption("Phase 1: reproducible strategy-family comparison. No parameter optimization.")

uploaded = st.file_uploader("Sube el workbook histórico corregido (.xlsx)", type=["xlsx"])

if uploaded is None:
    st.info("Carga el Excel histórico para validar los datos y ejecutar el backtest.")
    st.stop()

tmp = Path("/tmp/portfolio_strategy_lab_source.xlsx")
tmp.write_bytes(uploaded.getvalue())

try:
    assets = load_workbook(tmp)
    prices = close_matrix(assets)
    targets = load_targets(tmp)
except Exception as exc:
    st.error(f"No se pudo leer el workbook: {exc}")
    st.stop()

st.success(f"Workbook leído: {len(assets)} hojas de activos, {len(prices):,} fechas.")

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
st.write("Pesos detectados en TICKERS:", targets)
st.caption("Las filas OHLC inválidas no se usan en la matriz de cierres; no se corrigen silenciosamente.")

if st.button("Ejecutar Phase 1", type="primary"):
    with st.spinner("Ejecutando simulaciones..."):
        result = run_phase1(tmp)
    st.subheader("Resultados")
    if result.empty:
        st.warning("No se generaron resultados con este workbook.")
    else:
        display = result.copy()
        for col in ["CAGR", "ann_vol", "max_drawdown", "Sharpe", "Sortino", "Calmar"]:
            if col in display:
                display[col] = display[col].astype(float).round(4)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar resultados CSV",
            result.to_csv(index=False).encode("utf-8"),
            file_name="phase1_results.csv",
            mime="text/csv",
        )
