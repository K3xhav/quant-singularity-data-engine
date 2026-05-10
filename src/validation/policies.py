from __future__ import annotations

from datetime import time

import polars as pl

PREOPEN_CUTOFF = time(9, 15)
VALIDATION_STATUS_COLUMN = "validation_status"


def apply_options_duplicate_policy(
    df: pl.DataFrame,
    dataset: str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    if dataset != "options_chain":
        return df, _empty_quarantine_frame(df)

    required_columns = ["timestamp", "strike", "side"]
    if any(column_name not in df.columns for column_name in required_columns):
        return df, _empty_quarantine_frame(df)

    working = (
        _ensure_validation_status_column(df)
        .sort(_sort_columns(df))
        .with_row_index("__validation_order")
    )
    first_rows = working.group_by(required_columns, maintain_order=True).agg(
        pl.col("__validation_order").min().alias("__keep_order")
    )

    curated_df = (
        working.join(
            first_rows,
            left_on=required_columns + ["__validation_order"],
            right_on=required_columns + ["__keep_order"],
            how="semi",
        )
        .drop("__validation_order")
    )
    quarantine_df = (
        working.join(
            first_rows,
            left_on=required_columns + ["__validation_order"],
            right_on=required_columns + ["__keep_order"],
            how="anti",
        )
        .drop("__validation_order")
    )

    quarantine_df = _set_validation_status(
        quarantine_df,
        "DUPLICATE_OPTIONS_SNAPSHOT",
    )
    return curated_df, quarantine_df


def apply_timestamp_reordering(
    df: pl.DataFrame,
    dataset: str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    timestamp_col = _detect_timestamp_column(df)
    if timestamp_col is None:
        return _ensure_validation_status_column(df), _empty_quarantine_frame(df)

    working = _with_parsed_timestamps(_ensure_validation_status_column(df), timestamp_col)
    has_non_monotonic = working.filter(
        pl.col("__parsed_timestamp").is_not_null()
        & pl.col("__parsed_timestamp").shift(1).is_not_null()
        & (pl.col("__parsed_timestamp") < pl.col("__parsed_timestamp").shift(1))
    ).height > 0

    if not has_non_monotonic:
        return working.drop("__parsed_timestamp"), _empty_quarantine_frame(df)

    curated_df = (
        working.sort(_sort_columns(working))
        .drop("__parsed_timestamp")
    )
    curated_df = _append_validation_status(curated_df, "REORDERED_TIMESTAMPS")
    return curated_df, _empty_quarantine_frame(df)


def apply_ohlc_validation_policy(
    df: pl.DataFrame,
    dataset: str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    working = _ensure_validation_status_column(df)
    timestamp_col = _detect_timestamp_column(working)
    if timestamp_col is None:
        return working, _empty_quarantine_frame(working)

    working = _with_parsed_timestamps(working, timestamp_col)
    invalid_expr = _build_invalid_ohlc_expression(working)
    if invalid_expr is None:
        return working.drop("__parsed_timestamp"), _empty_quarantine_frame(working.drop("__parsed_timestamp"))

    invalid_rows = working.filter(invalid_expr)
    if invalid_rows.is_empty():
        return working.drop("__parsed_timestamp"), _empty_quarantine_frame(working.drop("__parsed_timestamp"))

    preserve_expr = _build_preopen_indicative_expression(working, dataset)
    anomaly_expr = invalid_expr & ~preserve_expr & _build_active_session_annotation_expression(
        working
    )

    curated_df = working
    curated_df = _append_status_by_mask(
        curated_df,
        _build_preopen_indicative_expression(curated_df, dataset),
        "PREOPEN_INDICATIVE",
    )
    curated_df = _append_status_by_mask(
        curated_df,
        anomaly_expr,
        "OHLC_ANOMALY",
    )
    curated_df = curated_df.drop("__parsed_timestamp")
    return curated_df, _empty_quarantine_frame(curated_df)


def _ensure_validation_status_column(df: pl.DataFrame) -> pl.DataFrame:
    if VALIDATION_STATUS_COLUMN in df.columns:
        return df
    return df.with_columns(pl.lit(None, dtype=pl.Utf8).alias(VALIDATION_STATUS_COLUMN))


def _empty_quarantine_frame(df: pl.DataFrame) -> pl.DataFrame:
    return _ensure_validation_status_column(df).head(0)


def _append_validation_status(df: pl.DataFrame, status: str) -> pl.DataFrame:
    if df.is_empty():
        return _ensure_validation_status_column(df)
    return df.with_columns(
        pl.when(pl.col(VALIDATION_STATUS_COLUMN).is_null())
        .then(pl.lit(status))
        .when(pl.col(VALIDATION_STATUS_COLUMN) == status)
        .then(pl.col(VALIDATION_STATUS_COLUMN))
        .otherwise(pl.col(VALIDATION_STATUS_COLUMN) + pl.lit("|") + pl.lit(status))
        .alias(VALIDATION_STATUS_COLUMN)
    )


def _set_validation_status(df: pl.DataFrame, status: str) -> pl.DataFrame:
    if df.is_empty():
        return _ensure_validation_status_column(df)
    return df.with_columns(pl.lit(status).alias(VALIDATION_STATUS_COLUMN))


def _append_status_by_mask(
    df: pl.DataFrame,
    mask: pl.Expr,
    status: str,
) -> pl.DataFrame:
    if df.is_empty():
        return _ensure_validation_status_column(df)
    return df.with_columns(
        pl.when(mask & pl.col(VALIDATION_STATUS_COLUMN).is_null())
        .then(pl.lit(status))
        .when(mask & (pl.col(VALIDATION_STATUS_COLUMN) == status))
        .then(pl.col(VALIDATION_STATUS_COLUMN))
        .when(mask)
        .then(pl.col(VALIDATION_STATUS_COLUMN) + pl.lit("|") + pl.lit(status))
        .otherwise(pl.col(VALIDATION_STATUS_COLUMN))
        .alias(VALIDATION_STATUS_COLUMN)
    )


def _with_parsed_timestamps(df: pl.DataFrame, timestamp_col: str) -> pl.DataFrame:
    return df.with_columns(_parse_timestamp_expr(timestamp_col).alias("__parsed_timestamp"))


def _parse_timestamp_expr(timestamp_col: str) -> pl.Expr:
    return (
        pl.when(pl.col(timestamp_col).is_null())
        .then(pl.lit(None, dtype=pl.Datetime))
        .otherwise(pl.col(timestamp_col).cast(pl.Utf8, strict=False).str.to_datetime(strict=False))
    )


def _build_invalid_ohlc_expression(df: pl.DataFrame) -> pl.Expr | None:
    expressions: list[pl.Expr] = []
    ohlc_groups = [
        ("open", "high", "low", "close"),
        ("near_month_open", "near_month_high", "near_month_low", "near_month_close"),
        ("mid_month_open", "mid_month_high", "mid_month_low", "mid_month_close"),
    ]
    for open_col, high_col, low_col, close_col in ohlc_groups:
        if any(column_name not in df.columns for column_name in (open_col, high_col, low_col, close_col)):
            continue
        expressions.append(
            (pl.col(low_col) > pl.col(open_col))
            | (pl.col(open_col) > pl.col(high_col))
            | (pl.col(low_col) > pl.col(close_col))
            | (pl.col(close_col) > pl.col(high_col))
        )

    if not expressions:
        return None

    combined = expressions[0]
    for expression in expressions[1:]:
        combined = combined | expression
    return combined


def _build_preopen_indicative_expression(df: pl.DataFrame, dataset: str) -> pl.Expr:
    if dataset != "options_chain":
        return pl.lit(False)
    required_columns = {"open", "high", "low", "close", "volume", "__parsed_timestamp"}
    if not required_columns.issubset(set(df.columns)):
        return pl.lit(False)

    invalid_base_ohlc = (
        (pl.col("low") > pl.col("open"))
        | (pl.col("open") > pl.col("high"))
        | (pl.col("low") > pl.col("close"))
        | (pl.col("close") > pl.col("high"))
    )
    return (
        invalid_base_ohlc
        & pl.col("__parsed_timestamp").is_not_null()
        & (pl.col("__parsed_timestamp").dt.time() < pl.lit(PREOPEN_CUTOFF))
        & (pl.col("volume") == 0)
    )


def _build_active_session_annotation_expression(df: pl.DataFrame) -> pl.Expr:
    if "__parsed_timestamp" not in df.columns:
        return pl.lit(False)

    expressions: list[pl.Expr] = []
    if {"open", "high", "low", "close", "volume"}.issubset(set(df.columns)):
        expressions.append(
            (
                (pl.col("low") > pl.col("open"))
                | (pl.col("open") > pl.col("high"))
                | (pl.col("low") > pl.col("close"))
                | (pl.col("close") > pl.col("high"))
            )
            & (pl.col("volume") > 0)
        )
    if {
        "near_month_open",
        "near_month_high",
        "near_month_low",
        "near_month_close",
        "near_month_volume",
    }.issubset(set(df.columns)):
        expressions.append(
            (
                (pl.col("near_month_low") > pl.col("near_month_open"))
                | (pl.col("near_month_open") > pl.col("near_month_high"))
                | (pl.col("near_month_low") > pl.col("near_month_close"))
                | (pl.col("near_month_close") > pl.col("near_month_high"))
            )
            & (pl.col("near_month_volume") > 0)
        )
    if {
        "mid_month_open",
        "mid_month_high",
        "mid_month_low",
        "mid_month_close",
        "mid_month_volume",
    }.issubset(set(df.columns)):
        expressions.append(
            (
                (pl.col("mid_month_low") > pl.col("mid_month_open"))
                | (pl.col("mid_month_open") > pl.col("mid_month_high"))
                | (pl.col("mid_month_low") > pl.col("mid_month_close"))
                | (pl.col("mid_month_close") > pl.col("mid_month_high"))
            )
            & (pl.col("mid_month_volume") > 0)
        )

    if not expressions:
        return pl.lit(False)

    combined = expressions[0]
    for expression in expressions[1:]:
        combined = combined | expression

    return (
        pl.col("__parsed_timestamp").is_not_null()
        & (pl.col("__parsed_timestamp").dt.time() >= pl.lit(PREOPEN_CUTOFF))
        & combined
    )


def _detect_timestamp_column(df: pl.DataFrame) -> str | None:
    for candidate in ("timestamp", "datetime", "date_time", "date"):
        if candidate in df.columns:
            return candidate
    return None


def _sort_columns(df: pl.DataFrame) -> list[str]:
    ordered_candidates = [
        "timestamp",
        "date",
        "strike",
        "side",
        "source_row_number",
    ]
    return [column_name for column_name in ordered_candidates if column_name in df.columns]
