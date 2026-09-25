# Portfolio Strategy Lab

Reproducible backtesting project for comparing portfolio strategy families before parameter optimization.

## Current status
Phase 1 engine, CSV-folder data normalization, deterministic simulation, metrics, risk-parity solver, and a Streamlit interface are in the repository.

## Data architecture
The historical Excel workbook is no longer part of the workflow. Each ticker is an independent CSV stored in `tickers/`, for example:

- `tickers/QQQ.csv`
- `tickers/BTC.csv`
- `tickers/SMH.csv`

The app reads these files directly from the repository. No historical workbook needs to be uploaded to ChatGPT or stored in the chat.

Current CSV exports use a ticker label on the first row and OHLC headers on the second row. The loader normalizes that format and flags invalid OHLC rows instead of silently repairing them.

## Phase 1
- Buy & Hold
- DCA
- Momentum
- Rotation
- Moving Average
- Dynamic Allocation
- Risk Parity
- Value is specified as a research family but is not fabricated without a comparable valuation dataset.

The ATR/pullback strategy is deliberately excluded from Phase 1 and will be tested later.

## Anti-overfitting protocol
1. Freeze Phase 1 definitions before inspecting performance.
2. Use the same universe, capital, contributions, costs and evaluation frequency where applicable.
3. Do not select parameters from historical results in Phase 1.
4. Use walk-forward / out-of-sample validation before Phase 2 optimization.
5. Prefer parameter plateaus and robustness over the single best historical result.
6. Keep an experiment log and immutable dataset/config versions.

## Online use
The app reads `tickers/*.csv` from the repository. No file upload is required. Install requirements and launch with `streamlit run app.py`.

## Data
The working universe uses BTC instead of IBIT. The old `Copia de QQQ` workbook sheet is no longer relevant. BTC OHLC anomalies are flagged/excluded rather than silently repaired.

## Workflow
GitHub `tickers/*.csv` -> validation/normalization -> strategy signals -> portfolio simulation -> metrics -> CSV summaries -> walk-forward/out-of-sample -> dashboard.

## Important
No strategy is declared "best" from one metric. Results are descriptive and should be evaluated across periods, drawdowns, turnover, cash drag, and out-of-sample behavior.
