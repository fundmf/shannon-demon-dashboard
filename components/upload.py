"""CSV upload + validation for OHLCV-style files exported from charting platforms.

Handles duplicate column names, mixed-timezone ISO timestamps, missing
indicator columns, irregular gaps, and short / constant series.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

import config as cfg

logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = ["close"]                                # absolute minimum
PREFERRED_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


@dataclass
class UploadResult:
    """Validated dataframe + parsing diagnostics surfaced to the UI."""

    df: pd.DataFrame
    interval: pd.Timedelta                  # median sampling interval
    interval_seconds: float
    n_rows: int
    n_dropped_dupes: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    has_time_index: bool = True


# ---------------------------------------------------------------------------
def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip, dedupe column names keeping the first occurrence."""
    cols = [str(c).strip() for c in df.columns]
    lowered = [c.lower() for c in cols]
    seen: dict[str, int] = {}
    keep_idx: list[int] = []
    for i, name in enumerate(lowered):
        # pandas auto-rename suffix -> ".1", ".2"; strip
        base = name.split(".")[0].strip()
        if base not in seen:
            seen[base] = i
            keep_idx.append(i)
    out = df.iloc[:, keep_idx].copy()
    out.columns = [lowered[i].split(".")[0].strip() for i in keep_idx]
    return out


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ---------------------------------------------------------------------------
def parse_csv(file_obj: io.BufferedReader | bytes | str) -> UploadResult:
    """Parse a CSV upload into a validated UploadResult.

    Args:
        file_obj: file-like object or raw bytes from Streamlit's file_uploader.

    Returns:
        UploadResult with the cleaned DataFrame plus diagnostics. Errors are
        accumulated in `errors`; the caller decides whether to render or block.
    """
    warnings_: list[str] = []
    errors_: list[str] = []

    try:
        df_raw = pd.read_csv(file_obj)
    except Exception as e:
        logger.exception("CSV parse failed")
        return UploadResult(
            df=pd.DataFrame(), interval=pd.Timedelta(0), interval_seconds=0.0,
            n_rows=0, n_dropped_dupes=0,
            errors=[f"Failed to read CSV: {e}"],
        )

    df = _normalise_columns(df_raw)
    df = _coerce_numeric(df, ["open", "high", "low", "close", "volume"])

    # ---- close column required ----
    if "close" not in df.columns:
        errors_.append("CSV must contain a 'close' column.")
        return UploadResult(
            df=pd.DataFrame(), interval=pd.Timedelta(0), interval_seconds=0.0,
            n_rows=0, n_dropped_dupes=0, errors=errors_,
        )

    if not pd.api.types.is_numeric_dtype(df["close"]):
        errors_.append("'close' column must be numeric — couldn't parse values as numbers.")
        return UploadResult(
            df=pd.DataFrame(), interval=pd.Timedelta(0), interval_seconds=0.0,
            n_rows=0, n_dropped_dupes=0, errors=errors_,
        )

    # ---- time parsing ----
    has_time = False
    if "time" in df.columns:
        try:
            t = pd.to_datetime(df["time"], utc=True, errors="coerce")
            if t.isna().any():
                warnings_.append(
                    f"{int(t.isna().sum())} rows had unparseable timestamps — dropped."
                )
                df = df.loc[~t.isna()].copy()
                t = t.dropna()
            df["time"] = t.dt.tz_convert("UTC").dt.tz_localize(None)
            df = df.sort_values("time").reset_index(drop=True)
            has_time = True
        except Exception as e:
            warnings_.append(f"Could not parse 'time' column ({e}); falling back to row index.")
    else:
        warnings_.append("No 'time' column found — using row index as the time axis.")

    # ---- duplicate timestamps ----
    n_dropped_dupes = 0
    if has_time:
        before = len(df)
        df = df.drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)
        n_dropped_dupes = before - len(df)
        if n_dropped_dupes > 0:
            warnings_.append(f"Dropped {n_dropped_dupes} duplicate timestamps (kept last).")

    # ---- close NaNs ----
    n_close_nan = int(df["close"].isna().sum())
    if n_close_nan > 0:
        warnings_.append(f"Dropped {n_close_nan} rows with NaN close values.")
        df = df.loc[df["close"].notna()].reset_index(drop=True)

    # ---- length checks ----
    n_rows = len(df)
    if n_rows < cfg.MIN_OBS_HARD_BLOCK:
        errors_.append(
            f"Only {n_rows} rows after cleaning — minimum {cfg.MIN_OBS_HARD_BLOCK} required."
        )
        return UploadResult(
            df=df, interval=pd.Timedelta(0), interval_seconds=0.0,
            n_rows=n_rows, n_dropped_dupes=n_dropped_dupes,
            warnings=warnings_, errors=errors_,
        )
    if n_rows < cfg.MIN_OBS_SOFT_WARN:
        warnings_.append(
            f"Only {n_rows} rows — statistical tests need ≥ {cfg.MIN_OBS_SOFT_WARN} for reliable estimates."
        )

    # ---- infer interval ----
    if has_time:
        diffs = df["time"].diff().dropna()
        if len(diffs) > 0:
            interval = diffs.median()
            if pd.isna(interval) or interval.total_seconds() <= 0:
                interval = pd.Timedelta(hours=1)
                warnings_.append("Could not infer sampling interval; defaulting to 1 hour.")
            # Gap detection
            gap_thresh = interval * cfg.GAP_WARN_MULTIPLIER
            n_gaps = int((diffs > gap_thresh).sum())
            if n_gaps > 0:
                warnings_.append(
                    f"{n_gaps} gaps larger than {cfg.GAP_WARN_MULTIPLIER}× the median interval — "
                    "weekends/holidays/data outages?"
                )
        else:
            interval = pd.Timedelta(hours=1)
            warnings_.append("Single-row time index; defaulting interval to 1 hour.")
    else:
        interval = pd.Timedelta(hours=1)
        warnings_.append("No time column — assuming 1-hour bars for annualisation.")

    # ---- constant series check ----
    if df["close"].nunique() < 3:
        errors_.append("'close' is constant or near-constant — no series variability to analyse.")
        return UploadResult(
            df=df, interval=interval, interval_seconds=interval.total_seconds(),
            n_rows=n_rows, n_dropped_dupes=n_dropped_dupes,
            warnings=warnings_, errors=errors_,
        )

    if has_time:
        df = df.set_index("time")

    logger.info(
        "Parsed %d rows, interval=%s, dupes=%d, warnings=%d",
        n_rows, interval, n_dropped_dupes, len(warnings_),
    )

    return UploadResult(
        df=df,
        interval=interval,
        interval_seconds=interval.total_seconds(),
        n_rows=n_rows,
        n_dropped_dupes=n_dropped_dupes,
        warnings=warnings_,
        errors=errors_,
        has_time_index=has_time,
    )


# ---------------------------------------------------------------------------
def render_uploader() -> Optional[UploadResult]:
    """Streamlit widget: file uploader + diagnostics panel.

    Returns:
        UploadResult on a valid file, else None (when no file uploaded).
    """
    uploaded = st.file_uploader(
        "Upload OHLCV CSV (TradingView export or compatible)",
        type=["csv"],
        help="Required column: close. Optional: time, open, high, low, volume.",
    )
    if uploaded is None:
        return None

    with st.spinner("Parsing CSV..."):
        result = parse_csv(uploaded)

    if result.errors:
        for err in result.errors:
            st.error(err)
        return None

    cols = st.columns(4)
    cols[0].metric("Rows", f"{result.n_rows:,}")
    cols[1].metric("Interval", str(result.interval).replace("0 days ", ""))
    cols[2].metric("Duplicates removed", f"{result.n_dropped_dupes}")
    cols[3].metric("Warnings", f"{len(result.warnings)}")

    if result.warnings:
        with st.expander(f"{len(result.warnings)} warning(s)"):
            for w in result.warnings:
                st.warning(w)

    return result
