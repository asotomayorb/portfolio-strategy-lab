# Results

Phase 1 results are generated only after the engine and tests pass.

Each run records:
- dataset version
- config version
- strategy
- evaluation frequency
- common-history and expanding-universe scope
- final value
- CAGR
- annualized volatility
- max drawdown
- Sharpe
- Sortino
- Calmar
- turnover
- trades
- cash diagnostics

No result file is considered an optimization result unless the experiment definition was frozen before performance inspection.

The first executable runner prepares the corrected workbook and reports coverage/missing-history diagnostics before any performance calculation.
