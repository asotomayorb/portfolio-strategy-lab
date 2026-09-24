# Source layout

Suggested modules:
- `data_loader.py` — read/normalize workbook
- `validation.py` — date, duplicates, missing values, corporate-action checks
- `signals.py` — strategy signals
- `portfolio.py` — holdings/cash/contributions/rebalancing
- `costs.py` — commissions/slippage
- `metrics.py` — performance/risk metrics
- `walk_forward.py` — train/validation/test windows
- `runner.py` — reproducible experiment runner

The first implementation should be a deterministic CLI/script. Avoid notebooks as the primary engine.
