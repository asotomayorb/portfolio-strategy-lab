# Data

Keep the original workbook separate from code logic and version it deliberately.

Expected source:
`BOLSA HISTORICOS corregido.xlsx`

Current data rules:
- TICKERS contains target allocations.
- Individual sheets contain OHLCV data.
- BTC replaces IBIT.
- `Copia de QQQ` is a backup sheet and must be ignored.
- INDA requires normalization/validation before use.
- Different assets have different history lengths; do not fabricate missing history.

Do not overwrite the original source. Create normalized derived data with a dataset version.
