from __future__ import annotations

from src.access.contracts import FuturesQuery, OptionsSnapshotQuery, SpotQuery, TimeRangeQuery
from src.access.queries import (
    get_features,
    get_features_batch,
    get_futures_data,
    get_min_timestamp,
    get_options_snapshot,
    get_range_bounds,
    get_signals,
    get_spot_data,
    get_time_range,
)


def run_access_demo() -> None:
    spot_timestamp = get_min_timestamp("nifty_spot")
    options_timestamp = get_min_timestamp("options_chain")
    futures_timestamp = get_min_timestamp("nifty_futures")
    range_start, range_end = get_range_bounds("india_vix")

    spot_frame = get_spot_data(SpotQuery(timestamp=spot_timestamp or ""))
    options_frame = get_options_snapshot(OptionsSnapshotQuery(timestamp=options_timestamp or ""))
    futures_frame = get_futures_data(FuturesQuery(timestamp=futures_timestamp or ""))
    range_frame = get_time_range(
        "india_vix",
        TimeRangeQuery(
            start_timestamp=range_start or "",
            end_timestamp=range_end or "",
        ),
    )
    features = get_features(spot_timestamp or "")
    signals = get_signals(spot_timestamp or "")
    features_batch = get_features_batch(
        start_timestamp=range_start or "",
        end_timestamp=range_end or "",
    )

    _print_summary("nifty_spot", spot_frame)
    _print_summary("options_chain", options_frame)
    _print_summary("nifty_futures", futures_frame)
    _print_summary("india_vix", range_frame)
    _print_feature_summary(features)
    _print_batch_summary(features_batch)
    _print_signal_summary(signals)


def _print_summary(dataset: str, frame) -> None:
    timestamp_column = "timestamp" if "timestamp" in frame.columns else None
    sample_timestamps: list[str] = []
    if timestamp_column is not None and not frame.is_empty():
        sample_timestamps = [str(value) for value in frame.get_column(timestamp_column).head(3).to_list()]

    print(f"Dataset: {dataset}")
    print(f"Rows returned: {frame.height}")
    print(f"Sample timestamps: {sample_timestamps}")


def _print_feature_summary(features: dict[str, object]) -> None:
    print("Features:")
    print(
        f"timestamp={features.get('timestamp')}, "
        f"spot_close={features.get('spot_close')}, "
        f"futures_close={features.get('futures_close')}, "
        f"vix_close={features.get('vix_close')}"
    )


def _print_batch_summary(frame) -> None:
    sample_timestamps: list[str] = []
    if "timestamp" in frame.columns and not frame.is_empty():
        sample_timestamps = [str(value) for value in frame.get_column("timestamp").head(3).to_list()]
    print("Features Batch:")
    print(f"Rows returned: {frame.height}")
    print(f"Sample timestamps: {sample_timestamps}")


def _print_signal_summary(signals: dict[str, object]) -> None:
    print("Signals:")
    print(
        f"timestamp={signals.get('timestamp')}, "
        f"spot_futures_spread={signals.get('spot_futures_spread')}, "
        f"vix_close={signals.get('vix_close')}"
    )
