from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import polars as pl

from src.profiling.models import ProfilingFinding, Severity

SAMPLE_SIZE = 5
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
DATASETS_WITH_DUPLICATE_TIMESTAMP_CHECK = {
    "nifty_spot",
    "nifty_futures",
    "india_vix",
}
DATASETS_WITH_MARKET_HOURS_CHECK = {
    "nifty_spot",
    "nifty_futures",
    "india_vix",
    "options_chain",
}
DATASET_INTERVAL_MINUTES = {
    "options_chain": 5,
    "nifty_spot": 1,
    "india_vix": 1,
    "nifty_futures": 1,
}
PRICE_TOKENS = (
    "open",
    "high",
    "low",
    "close",
    "price",
    "ltp",
    "strike",
    "premium",
    "settle",
    "vix",
)
PRICE_EXCLUDE_TOKENS = ("change", "pct", "percent", "return")
IV_TOKENS = ("iv", "implied_vol")


def check_nulls(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
) -> list[ProfilingFinding]:
    if dataset == "nse_calendar":
        return _check_nse_calendar_nulls(df=df, dataset=dataset, file_name=file_name)

    findings: list[ProfilingFinding] = []
    for column_name in df.columns:
        null_rows = df.filter(pl.col(column_name).is_null())
        if null_rows.is_empty():
            continue

        findings.append(
            _build_finding(
                dataset=dataset,
                file_name=file_name,
                severity=Severity.WARNING,
                rule=f"null_values:{column_name}",
                message=f"Column '{column_name}' contains null values.",
                rows=null_rows,
                timestamp_col=_detect_timestamp_column(df),
            )
        )
    return findings


def check_duplicate_timestamps(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
    timestamp_col: str = "timestamp",
) -> list[ProfilingFinding]:
    if dataset not in DATASETS_WITH_DUPLICATE_TIMESTAMP_CHECK:
        return []
    if timestamp_col not in df.columns:
        return []

    duplicates = df.filter(pl.col(timestamp_col).is_duplicated())
    if duplicates.is_empty():
        return []

    return [
        _build_finding(
            dataset=dataset,
            file_name=file_name,
            severity=Severity.CRITICAL,
            rule="duplicate_timestamps",
            message=f"Duplicate values detected in '{timestamp_col}'.",
            rows=duplicates,
            timestamp_col=timestamp_col,
        )
    ]


def check_monotonic_timestamps(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
    timestamp_col: str = "timestamp",
) -> list[ProfilingFinding]:
    if timestamp_col not in df.columns:
        return []

    timestamp_frame = _with_parsed_timestamps(df, timestamp_col)
    invalid_rows = timestamp_frame.filter(
        pl.col("__parsed_timestamp").is_not_null()
        & pl.col("__parsed_timestamp").shift(1).is_not_null()
        & (pl.col("__parsed_timestamp") < pl.col("__parsed_timestamp").shift(1))
    ).drop("__parsed_timestamp")

    if invalid_rows.is_empty():
        return []

    return [
        _build_finding(
            dataset=dataset,
            file_name=file_name,
            severity=Severity.WARNING,
            rule="non_monotonic_timestamps",
            message=f"Timestamp order decreases in '{timestamp_col}'.",
            rows=invalid_rows,
            timestamp_col=timestamp_col,
        )
    ]


def check_missing_intervals(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
    timestamp_col: str = "timestamp",
) -> list[ProfilingFinding]:
    interval_minutes = DATASET_INTERVAL_MINUTES.get(dataset)
    if interval_minutes is None:
        return []
    if timestamp_col not in df.columns:
        return []

    timestamp_frame = _with_parsed_timestamps(df, timestamp_col)
    parsed_timestamps = (
        timestamp_frame.select(pl.col("__parsed_timestamp"))
        .filter(pl.col("__parsed_timestamp").is_not_null())
        .unique()
        .sort("__parsed_timestamp")
        .get_column("__parsed_timestamp")
        .to_list()
    )
    if len(parsed_timestamps) < 2:
        return []

    expected_delta = timedelta(minutes=interval_minutes)
    missing_timestamps: list[datetime] = []
    sample_gap_rows: list[dict[str, str | int]] = []

    timestamps_by_date: dict[datetime.date, list[datetime]] = {}
    for parsed_timestamp in parsed_timestamps:
        timestamps_by_date.setdefault(parsed_timestamp.date(), []).append(parsed_timestamp)

    for trading_date in sorted(timestamps_by_date):
        day_timestamps = timestamps_by_date[trading_date]
        for previous_timestamp, current_timestamp in zip(day_timestamps, day_timestamps[1:]):
            if current_timestamp <= previous_timestamp:
                continue

            gap_missing_timestamps = _build_missing_gap(
                previous_timestamp=previous_timestamp,
                current_timestamp=current_timestamp,
                expected_delta=expected_delta,
            )
            if not gap_missing_timestamps:
                continue

            missing_timestamps.extend(gap_missing_timestamps)
            if len(sample_gap_rows) < SAMPLE_SIZE:
                sample_gap_rows.append(
                    {
                        "previous_timestamp": previous_timestamp.isoformat(sep=" "),
                        "next_timestamp": current_timestamp.isoformat(sep=" "),
                        "missing_intervals": len(gap_missing_timestamps),
                        "first_missing_timestamp": gap_missing_timestamps[0].isoformat(sep=" "),
                    }
                )

    if not missing_timestamps:
        return []

    first_missing = missing_timestamps[0].isoformat(sep=" ")
    severity = Severity.WARNING if len(missing_timestamps) <= 3 else Severity.CRITICAL
    return [
        ProfilingFinding(
            dataset=dataset,
            file_name=file_name,
            severity=severity,
            rule="missing_intervals",
            message=(
                f"Detected {len(missing_timestamps)} missing interval(s); "
                f"first missing timestamp: {first_missing}."
            ),
            affected_rows=len(missing_timestamps),
            sample_rows=sample_gap_rows,
            timestamp=first_missing,
        )
    ]


def check_ohlc_integrity(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
) -> list[ProfilingFinding]:
    findings: list[ProfilingFinding] = []
    ohlc_groups = [
        (
            "ohlc_integrity",
            "OHLC bounds violated: expected low <= open/close <= high.",
            ("open", "high", "low", "close"),
        ),
        (
            "near_month_ohlc_integrity",
            "Near month OHLC bounds violated: expected low <= open/close <= high.",
            (
                "near_month_open",
                "near_month_high",
                "near_month_low",
                "near_month_close",
            ),
        ),
        (
            "mid_month_ohlc_integrity",
            "Mid month OHLC bounds violated: expected low <= open/close <= high.",
            (
                "mid_month_open",
                "mid_month_high",
                "mid_month_low",
                "mid_month_close",
            ),
        ),
    ]

    for rule, message, columns in ohlc_groups:
        open_col, high_col, low_col, close_col = columns
        if any(column_name not in df.columns for column_name in columns):
            continue

        invalid_rows = df.filter(
            (pl.col(low_col) > pl.col(open_col))
            | (pl.col(open_col) > pl.col(high_col))
            | (pl.col(low_col) > pl.col(close_col))
            | (pl.col(close_col) > pl.col(high_col))
        )
        if invalid_rows.is_empty():
            continue

        findings.append(
            _build_finding(
                dataset=dataset,
                file_name=file_name,
                severity=Severity.CRITICAL,
                rule=rule,
                message=message,
                rows=invalid_rows,
                timestamp_col=_detect_timestamp_column(df),
            )
        )

    return findings


def check_negative_values(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
) -> list[ProfilingFinding]:
    findings: list[ProfilingFinding] = []
    for column_name in df.columns:
        if not _is_numeric_dtype(df.schema[column_name]):
            continue
        if not _should_check_negative(column_name):
            continue

        invalid_rows = df.filter(pl.col(column_name) < 0)
        if invalid_rows.is_empty():
            continue

        findings.append(
            _build_finding(
                dataset=dataset,
                file_name=file_name,
                severity=Severity.CRITICAL,
                rule=f"negative_values:{column_name}",
                message=f"Column '{column_name}' contains negative values.",
                rows=invalid_rows,
                timestamp_col=_detect_timestamp_column(df),
            )
        )
    return findings


def check_market_hours(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
    timestamp_col: str = "timestamp",
) -> list[ProfilingFinding]:
    if dataset not in DATASETS_WITH_MARKET_HOURS_CHECK:
        return []
    if timestamp_col not in df.columns:
        return []

    timestamp_frame = _with_parsed_timestamps(df, timestamp_col)
    outside_hours = timestamp_frame.filter(
        pl.col("__parsed_timestamp").is_not_null()
        & (
            (pl.col("__parsed_timestamp").dt.time() < pl.lit(MARKET_OPEN))
            | (pl.col("__parsed_timestamp").dt.time() > pl.lit(MARKET_CLOSE))
        )
    ).drop("__parsed_timestamp")

    if outside_hours.is_empty():
        return []

    return [
        _build_finding(
            dataset=dataset,
            file_name=file_name,
            severity=Severity.INFO,
            rule="outside_market_hours",
            message="Rows detected outside 09:15 to 15:30 IST market hours.",
            rows=outside_hours,
            timestamp_col=timestamp_col,
        )
    ]


def check_options_uniqueness(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
) -> list[ProfilingFinding]:
    required_columns = ["timestamp", "strike", "side"]
    if any(column_name not in df.columns for column_name in required_columns):
        return []

    duplicate_combinations = df.filter(pl.struct(required_columns).is_duplicated())
    if duplicate_combinations.is_empty():
        return []

    return [
        _build_finding(
            dataset=dataset,
            file_name=file_name,
            severity=Severity.CRITICAL,
            rule="options_uniqueness",
            message="Duplicate (timestamp, strike, side) combinations detected.",
            rows=duplicate_combinations,
            timestamp_col="timestamp",
        )
    ]


def run_all_checks(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
    timestamp_col: str | None = None,
) -> list[ProfilingFinding]:
    resolved_timestamp_col = timestamp_col or _detect_timestamp_column(df) or "timestamp"
    findings: list[ProfilingFinding] = []
    findings.extend(check_nulls(df=df, dataset=dataset, file_name=file_name))
    findings.extend(
        check_duplicate_timestamps(
            df=df,
            dataset=dataset,
            file_name=file_name,
            timestamp_col=resolved_timestamp_col,
        )
    )
    findings.extend(
        check_monotonic_timestamps(
            df=df,
            dataset=dataset,
            file_name=file_name,
            timestamp_col=resolved_timestamp_col,
        )
    )
    findings.extend(
        check_missing_intervals(
            df=df,
            dataset=dataset,
            file_name=file_name,
            timestamp_col=resolved_timestamp_col,
        )
    )
    findings.extend(check_ohlc_integrity(df=df, dataset=dataset, file_name=file_name))
    findings.extend(check_negative_values(df=df, dataset=dataset, file_name=file_name))
    findings.extend(
        check_market_hours(
            df=df,
            dataset=dataset,
            file_name=file_name,
            timestamp_col=resolved_timestamp_col,
        )
    )
    findings.extend(check_options_uniqueness(df=df, dataset=dataset, file_name=file_name))
    return findings


def _build_finding(
    dataset: str,
    file_name: str,
    severity: Severity,
    rule: str,
    message: str,
    rows: pl.DataFrame,
    timestamp_col: str | None,
) -> ProfilingFinding:
    sample_rows = _sample_rows(rows)
    return ProfilingFinding(
        dataset=dataset,
        file_name=file_name,
        severity=severity,
        rule=rule,
        message=message,
        affected_rows=rows.height,
        sample_rows=sample_rows,
        timestamp=_extract_timestamp(sample_rows, timestamp_col),
    )


def _with_parsed_timestamps(df: pl.DataFrame, timestamp_col: str) -> pl.DataFrame:
    series = df.get_column(timestamp_col)
    parsed_series = _parse_timestamp_series(series)
    return df.with_columns(parsed_series.alias("__parsed_timestamp"))


def _parse_timestamp_series(series: pl.Series) -> pl.Series:
    if series.dtype == pl.Datetime:
        return series
    if series.dtype == pl.Date:
        return series.cast(pl.Datetime)

    as_text = series.cast(pl.Utf8, strict=False)
    parsed = as_text.str.to_datetime(strict=False)
    if parsed.null_count() < len(series):
        return parsed

    return as_text.str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False)


def _build_missing_gap(
    previous_timestamp: datetime,
    current_timestamp: datetime,
    expected_delta: timedelta,
) -> list[datetime]:
    missing_timestamps: list[datetime] = []
    next_timestamp = previous_timestamp + expected_delta
    while next_timestamp < current_timestamp:
        missing_timestamps.append(next_timestamp)
        next_timestamp = next_timestamp + expected_delta
    return missing_timestamps


def _sample_rows(rows: pl.DataFrame) -> list[dict]:
    return [_normalize_row(row) for row in rows.head(SAMPLE_SIZE).iter_rows(named=True)]


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in sorted(row):
        value = row[key]
        if isinstance(value, datetime):
            normalized[key] = value.isoformat(sep=" ")
        else:
            normalized[key] = value
    return normalized


def _extract_timestamp(sample_rows: list[dict], timestamp_col: str | None) -> str | None:
    if not sample_rows or timestamp_col is None:
        return None

    raw_timestamp = sample_rows[0].get(timestamp_col)
    if raw_timestamp is None:
        return None
    if isinstance(raw_timestamp, datetime):
        return raw_timestamp.isoformat(sep=" ")
    return str(raw_timestamp)


def _detect_timestamp_column(df: pl.DataFrame) -> str | None:
    candidates = ("timestamp", "datetime", "date_time", "time", "date")
    lower_to_actual = {column_name.lower(): column_name for column_name in df.columns}
    for candidate in candidates:
        if candidate in lower_to_actual:
            return lower_to_actual[candidate]
    return None


def _is_numeric_dtype(dtype: pl.DataType) -> bool:
    return dtype.is_numeric()


def _should_check_negative(column_name: str) -> bool:
    lowered = column_name.lower()
    if "volume" in lowered:
        return True
    if any(token in lowered for token in IV_TOKENS):
        return True
    if any(token in lowered for token in PRICE_EXCLUDE_TOKENS):
        return False
    return any(token in lowered for token in PRICE_TOKENS)


def _check_nse_calendar_nulls(
    df: pl.DataFrame,
    dataset: str,
    file_name: str,
) -> list[ProfilingFinding]:
    findings: list[ProfilingFinding] = []
    if "is_trading_day" not in df.columns:
        return findings

    trading_day_expression = pl.col("is_trading_day") == True
    for column_name in ("session_start", "session_end"):
        if column_name not in df.columns:
            continue

        null_rows = df.filter(trading_day_expression & pl.col(column_name).is_null())
        if null_rows.is_empty():
            continue

        findings.append(
            _build_finding(
                dataset=dataset,
                file_name=file_name,
                severity=Severity.WARNING,
                rule=f"null_values:{column_name}",
                message=f"Column '{column_name}' contains null values on trading days.",
                rows=null_rows,
                timestamp_col=_detect_timestamp_column(df),
            )
        )
    return findings
