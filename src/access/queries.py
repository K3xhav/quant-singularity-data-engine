from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl

from src.access.contracts import FuturesQuery, OptionsSnapshotQuery, SpotQuery, TimeRangeQuery

CURATED_ROOT = Path("data/warehouse/curated")
DATASET_PATHS = {
    "nifty_spot": CURATED_ROOT / "nifty_spot" / "*.parquet",
    "options_chain": CURATED_ROOT / "options_chain" / "*.parquet",
    "nifty_futures": CURATED_ROOT / "nifty_futures" / "*.parquet",
    "india_vix": CURATED_ROOT / "india_vix" / "*.parquet",
}


def create_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database=":memory:")


def get_spot_data(query: SpotQuery) -> pl.DataFrame:
    sql = f"""
        SELECT *
        FROM read_parquet(?)
        WHERE timestamp = ?
        ORDER BY timestamp, source_row_number
    """
    return _execute_query(sql=sql, parameters=[_dataset_glob("nifty_spot"), query.timestamp])


def get_options_snapshot(query: OptionsSnapshotQuery) -> pl.DataFrame:
    conditions = ["timestamp = ?"]
    parameters: list[str | int] = [query.timestamp]

    if query.strike is not None:
        conditions.append("strike = ?")
        parameters.append(query.strike)
    if query.side is not None:
        conditions.append("side = ?")
        parameters.append(query.side)

    sql = f"""
        SELECT *
        FROM read_parquet(?)
        WHERE {" AND ".join(conditions)}
        ORDER BY timestamp, strike, side, source_row_number
    """
    return _execute_query(
        sql=sql,
        parameters=[_dataset_glob("options_chain"), *parameters],
    )


def get_futures_data(query: FuturesQuery) -> pl.DataFrame:
    sql = f"""
        SELECT *
        FROM read_parquet(?)
        WHERE timestamp = ?
        ORDER BY timestamp, source_row_number
    """
    return _execute_query(sql=sql, parameters=[_dataset_glob("nifty_futures"), query.timestamp])


def get_time_range(dataset: str, query: TimeRangeQuery) -> pl.DataFrame:
    if dataset not in DATASET_PATHS:
        raise ValueError(f"Unsupported dataset: {dataset}")

    timestamp_column = _timestamp_column_for_dataset(dataset)
    sql = f"""
        SELECT *
        FROM read_parquet(?)
        WHERE {timestamp_column} >= ? AND {timestamp_column} <= ?
        ORDER BY {_order_by_clause(dataset)}
    """
    return _execute_query(
        sql=sql,
        parameters=[_dataset_glob(dataset), query.start_timestamp, query.end_timestamp],
    )


def get_min_timestamp(dataset: str) -> str | None:
    if dataset not in DATASET_PATHS:
        raise ValueError(f"Unsupported dataset: {dataset}")

    timestamp_column = _timestamp_column_for_dataset(dataset)
    sql = f"""
        SELECT MIN({timestamp_column}) AS min_timestamp
        FROM read_parquet(?)
    """
    frame = _execute_query(sql=sql, parameters=[_dataset_glob(dataset)])
    if frame.is_empty():
        return None
    value = frame.item(0, "min_timestamp")
    if value is None:
        return None
    return str(value)


def get_range_bounds(dataset: str) -> tuple[str | None, str | None]:
    if dataset not in DATASET_PATHS:
        raise ValueError(f"Unsupported dataset: {dataset}")

    timestamp_column = _timestamp_column_for_dataset(dataset)
    sql = f"""
        SELECT
            MIN({timestamp_column}) AS min_timestamp,
            MAX({timestamp_column}) AS max_timestamp
        FROM read_parquet(?)
    """
    frame = _execute_query(sql=sql, parameters=[_dataset_glob(dataset)])
    if frame.is_empty():
        return None, None
    min_value = frame.item(0, "min_timestamp")
    max_value = frame.item(0, "max_timestamp")
    return (
        None if min_value is None else str(min_value),
        None if max_value is None else str(max_value),
    )


def get_features(timestamp: str) -> dict[str, object]:
    spot_frame = get_spot_data(SpotQuery(timestamp=timestamp))
    futures_frame = get_futures_data(FuturesQuery(timestamp=timestamp))
    vix_frame = get_time_range(
        "india_vix",
        TimeRangeQuery(start_timestamp=timestamp, end_timestamp=timestamp),
    )

    return {
        "timestamp": timestamp,
        "spot_close": _get_scalar_value(spot_frame, "close"),
        "futures_close": _get_scalar_value(futures_frame, "near_month_close"),
        "vix_close": _get_scalar_value(vix_frame, "vix_close"),
        "spot_has_validation_metadata": "validation_status" in spot_frame.columns,
        "futures_has_validation_metadata": "validation_status" in futures_frame.columns,
        "vix_has_validation_metadata": "validation_status" in vix_frame.columns,
    }


def get_features_batch(start_timestamp: str, end_timestamp: str) -> pl.DataFrame:
    range_query = TimeRangeQuery(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    spot_frame = get_time_range("nifty_spot", range_query).select(
        [
            "timestamp",
            pl.col("close").alias("spot_close"),
            pl.col("validation_status").alias("spot_validation_status"),
        ]
    )
    futures_frame = get_time_range("nifty_futures", range_query).select(
        [
            "timestamp",
            pl.col("near_month_close").alias("futures_close"),
            pl.col("validation_status").alias("futures_validation_status"),
        ]
    )
    vix_frame = get_time_range("india_vix", range_query).select(
        [
            "timestamp",
            pl.col("vix_close"),
            pl.col("validation_status").alias("vix_validation_status"),
        ]
    )

    if spot_frame.is_empty() or futures_frame.is_empty() or vix_frame.is_empty():
        return pl.DataFrame()

    return (
        spot_frame.join(futures_frame, on="timestamp", how="inner")
        .join(vix_frame, on="timestamp", how="inner")
        .sort("timestamp")
    )


def get_signals(timestamp: str) -> dict[str, object]:
    features = get_features(timestamp)
    spot_close = features.get("spot_close")
    futures_close = features.get("futures_close")
    vix_close = features.get("vix_close")
    spread = None
    if isinstance(spot_close, (int, float)) and isinstance(futures_close, (int, float)):
        spread = float(futures_close) - float(spot_close)

    return {
        "timestamp": timestamp,
        "spot_close": spot_close,
        "futures_close": futures_close,
        "vix_close": vix_close,
        "spot_futures_spread": spread,
    }


def _execute_query(sql: str, parameters: list[str | int]) -> pl.DataFrame:
    with create_connection() as connection:
        arrow_table = connection.execute(sql, parameters).arrow()
    return pl.from_arrow(arrow_table)


def _dataset_glob(dataset: str) -> str:
    return str(DATASET_PATHS[dataset])


def _timestamp_column_for_dataset(dataset: str) -> str:
    if dataset in {"nifty_spot", "options_chain", "nifty_futures", "india_vix"}:
        return "timestamp"
    raise ValueError(f"Unsupported dataset: {dataset}")


def _order_by_clause(dataset: str) -> str:
    if dataset == "options_chain":
        return "timestamp, strike, side, source_row_number"
    return "timestamp, source_row_number"


def _get_scalar_value(frame: pl.DataFrame, column_name: str) -> object:
    if frame.is_empty() or column_name not in frame.columns:
        return None
    return frame.item(0, column_name)
