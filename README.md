# Portfolio Strategy Lab

Reproducible backtesting project for comparing portfolio strategy families before parameter optimization.

## Current status
Phase 1 engine, data normalization, deterministic simulation, metrics, risk-parity solver, preliminary real-data results, and an uploadable Streamlit interface are in the repository.

The historical workbook is intentionally not committed to GitHub. The online interface accepts the corrected .xlsx directly, so the source dataset can remain private.

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
Install the requirements and launch Streamlit with: streamlit run app.py. Upload the corrected historical workbook, inspect the data-quality table, then run Phase 1 and download the CSV.

## Data
The working universe uses BTC instead of IBIT. The backup sheet Copia de QQQ is ignored. BTC OHLC anomalies are flagged/excluded rather than silently repaired.

## Workflow
Raw data -> validation/normalization -> strategy signals -> portfolio simulation -> metrics -> CSV summaries -> walk-forward/out-of-sample -> dashboard.

## Important
No strategy is declared "best" from one metric. Results are descriptive and should be evaluated across periods, drawdowns, turnover, cash drag, and out-of-sample behavior.
