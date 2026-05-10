# Profiling Summary

Total findings: **26**

## Findings by Severity
- CRITICAL: 13
- WARNING: 1
- INFO: 12

## Findings by Dataset
- options_chain: 26

## Top Recurring Anomaly Types
- ohlc_integrity: 12
- outside_market_hours: 12
- non_monotonic_timestamps: 1
- options_uniqueness: 1

## Affected Dataset Counts
- non_monotonic_timestamps: 1
- ohlc_integrity: 1
- options_uniqueness: 1
- outside_market_hours: 1

## Engineering Observations
- Most frequent anomaly type: `ohlc_integrity` (12 findings).
- Highest anomaly concentration: `options_chain` (26 findings).
- Critical issues remain concentrated in market data integrity checks (13 findings).

## Severity Details
### CRITICAL
- `options_chain` / `2025-08-22_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1795.
- `options_chain` / `2025-08-22_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1831.
- `options_chain` / `2025-08-25_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1831.
- `options_chain` / `2025-08-25_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1819.
- `options_chain` / `2025-08-26_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1828.
- `options_chain` / `2025-08-26_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1795.
- `options_chain` / `2025-08-27_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1817.
- `options_chain` / `2025-08-27_2025-08-28.csv` / `options_uniqueness`: Duplicate (timestamp, strike, side) combinations detected. Affected rows: 12.
- `options_chain` / `2025-08-27_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1887.
- `options_chain` / `2025-08-28_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1820.
- `options_chain` / `2025-08-28_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1869.
- `options_chain` / `2025-09-01_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1892.
- `options_chain` / `2025-09-02_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1846.
### WARNING
- `options_chain` / `2025-08-27_2025-08-28.csv` / `non_monotonic_timestamps`: Timestamp order decreases in 'timestamp'. Affected rows: 1.
### INFO
- `options_chain` / `2025-08-22_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-22_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-25_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-25_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-26_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-26_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-27_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-27_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-28_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-08-28_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-09-01_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- `options_chain` / `2025-09-02_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.

## Dataset Details
### options_chain
- [CRITICAL] `2025-08-22_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1795.
- [CRITICAL] `2025-08-22_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1831.
- [CRITICAL] `2025-08-25_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1831.
- [CRITICAL] `2025-08-25_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1819.
- [CRITICAL] `2025-08-26_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1828.
- [CRITICAL] `2025-08-26_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1795.
- [CRITICAL] `2025-08-27_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1817.
- [CRITICAL] `2025-08-27_2025-08-28.csv` / `options_uniqueness`: Duplicate (timestamp, strike, side) combinations detected. Affected rows: 12.
- [CRITICAL] `2025-08-27_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1887.
- [CRITICAL] `2025-08-28_2025-08-28.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1820.
- [CRITICAL] `2025-08-28_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1869.
- [CRITICAL] `2025-09-01_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1892.
- [CRITICAL] `2025-09-02_2025-09-25.csv` / `ohlc_integrity`: OHLC bounds violated: expected low <= open/close <= high. Affected rows: 1846.
- [WARNING] `2025-08-27_2025-08-28.csv` / `non_monotonic_timestamps`: Timestamp order decreases in 'timestamp'. Affected rows: 1.
- [INFO] `2025-08-22_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-22_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-25_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-25_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-26_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-26_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-27_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-27_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-28_2025-08-28.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-08-28_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-09-01_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
- [INFO] `2025-09-02_2025-09-25.csv` / `outside_market_hours`: Rows detected outside 09:15 to 15:30 IST market hours. Affected rows: 174.
