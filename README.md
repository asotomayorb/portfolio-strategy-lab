# Portfolio Strategy Lab

Reproducible backtesting project for comparing portfolio strategy families before parameter optimization.

## Objective
Phase 1 compares:
- Buy & Hold
- DCA
- Momentum
- Value
- Rotation
- Moving Average
- Dynamic Allocation
- Risk Parity

The ATR/pullback strategy is deliberately excluded from Phase 1 and will be tested later.

## Anti-overfitting protocol
1. Freeze Phase 1 definitions before inspecting performance.
2. Use the same universe, capital, contributions, costs and evaluation frequency where applicable.
3. Do not select parameters from historical results in Phase 1.
4. Use walk-forward / out-of-sample validation before Phase 2 optimization.
5. Prefer parameter plateaus and robustness over the single best historical result.
6. Keep an experiment log and immutable dataset/config versions.

## Data
The working universe now uses BTC instead of IBIT. The backup sheet `Copia de QQQ` is ignored.
The corrected historical workbook will be validated before being added as the project dataset.

## Workflow
Raw data -> validation/normalization -> strategy signals -> portfolio simulation -> metrics -> CSV summaries -> Google Sheets dashboard.

## Important
No strategy is declared "best" from one metric. Selection is based on robustness across periods, drawdowns, turnover, cash drag, and out-of-sample behavior.
