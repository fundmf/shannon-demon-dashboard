"""Shannon's Demon backtest — sleeve-A simulation on the uploaded asset.

Models a two-asset (risky + cash) sleeve with three rebalance rules:
    - time:      every N periods
    - threshold: when the risky weight drifts ±X% from target
    - band:      when the price crosses ±Nσ of a rolling mean
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

RebalanceRule = Literal["time", "threshold", "band"]


@dataclass
class BacktestResult:
    """Output of a single demon backtest."""

    equity_curve: pd.Series
    risky_value: pd.Series
    cash_value: pd.Series
    rebalance_events: list[int]                # row indices where rebalance occurred
    n_rebalances: int
    total_costs: float
    cagr: float
    annualised_vol: float
    max_drawdown: float
    sharpe: float
    sortino: float
    final_value: float


# ---------------------------------------------------------------------------
def _annualisation_factor(interval_seconds: float, annualisation: str) -> float:
    if interval_seconds <= 0:
        interval_seconds = 3600.0
    if annualisation == "calendar":
        return (365.25 * 24 * 3600) / interval_seconds
    return (252 * 24 * 3600) / interval_seconds


def _max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peaks = np.maximum.accumulate(equity)
    dd = (equity - peaks) / peaks
    return float(dd.min())


def _sharpe(returns: np.ndarray, ppy: float, rf_annual: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - rf_annual / ppy
    sd = excess.std(ddof=1)
    if sd <= 0:
        return 0.0
    return float(excess.mean() / sd * np.sqrt(ppy))


def _sortino(returns: np.ndarray, ppy: float, mar_annual: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - mar_annual / ppy
    downside = excess[excess < 0]
    if len(downside) < 2:
        return 0.0
    dd = downside.std(ddof=1)
    if dd <= 0:
        return 0.0
    return float(excess.mean() / dd * np.sqrt(ppy))


# ---------------------------------------------------------------------------
def run_demon_backtest(
    close: pd.Series,
    *,
    weight: float = 0.5,
    rebalance_rule: RebalanceRule = "time",
    time_period: int = 24,
    threshold_pct: float = 10.0,
    band_sigma: float = 1.0,
    band_window: int = 90,
    cash_yield_annual_pct: float = 0.0,
    transaction_cost_bps: float = 5.0,
    interval_seconds: float = 3600.0,
    annualisation: str = "trading",
    initial_capital: float = 1.0,
) -> BacktestResult:
    """Simulate Shannon's Demon rebalancing on a price series.

    Args:
        close: price series indexed by time.
        weight: target risky-asset weight (0..1).
        rebalance_rule: 'time' | 'threshold' | 'band'.
        time_period: rebalance every N periods (rule='time').
        threshold_pct: drift % from target (rule='threshold').
        band_sigma: σ-multiple from rolling mean (rule='band').
        band_window: rolling window for band rule.
        cash_yield_annual_pct: cash leg annual yield in %.
        transaction_cost_bps: bps charged on the gross rebalance turnover.
        interval_seconds: median bar interval, used for annualisation.
        annualisation: 'trading' or 'calendar'.
        initial_capital: seed capital.

    Returns:
        BacktestResult with equity curve and headline metrics.
    """
    if len(close) < 5:
        raise ValueError("close series too short for backtest")

    prices = close.to_numpy(dtype=float)
    n = len(prices)
    cost_rate = transaction_cost_bps / 10_000.0

    ppy = _annualisation_factor(interval_seconds, annualisation)
    cash_yield_per_period = cash_yield_annual_pct / 100.0 / ppy

    # Initialise sleeve
    risky_val = initial_capital * weight
    cash_val = initial_capital * (1 - weight)
    n_shares = risky_val / prices[0] if prices[0] > 0 else 0.0

    equity_arr = np.zeros(n)
    risky_arr = np.zeros(n)
    cash_arr = np.zeros(n)
    rebalance_events: list[int] = []
    total_cost_paid = 0.0

    # Pre-compute band reference
    rolling_mean = close.rolling(band_window, min_periods=max(10, band_window // 3)).mean()
    rolling_std = close.rolling(band_window, min_periods=max(10, band_window // 3)).std()

    for i in range(n):
        risky_val = n_shares * prices[i]
        cash_val *= (1 + cash_yield_per_period)
        total = risky_val + cash_val

        # Decide whether to rebalance at end of bar
        do_rebalance = False
        if i > 0 and total > 0:
            current_w = risky_val / total
            if rebalance_rule == "time":
                do_rebalance = (i % max(1, int(time_period))) == 0
            elif rebalance_rule == "threshold":
                drift = abs(current_w - weight)
                do_rebalance = drift > (threshold_pct / 100.0)
            elif rebalance_rule == "band":
                rm = rolling_mean.iloc[i]
                rs = rolling_std.iloc[i]
                if np.isfinite(rm) and np.isfinite(rs) and rs > 0:
                    z = (prices[i] - rm) / rs
                    do_rebalance = abs(z) > band_sigma

        if do_rebalance:
            target_risky = total * weight
            turnover = abs(target_risky - risky_val)
            cost = turnover * cost_rate
            total_cost_paid += cost
            # Apply cost to cash leg
            cash_val = total - target_risky - cost
            risky_val = target_risky
            n_shares = risky_val / prices[i] if prices[i] > 0 else 0.0
            rebalance_events.append(i)

        equity_arr[i] = risky_val + cash_val
        risky_arr[i] = risky_val
        cash_arr[i] = cash_val

    equity = pd.Series(equity_arr, index=close.index, name="equity")
    risky_s = pd.Series(risky_arr, index=close.index, name="risky")
    cash_s = pd.Series(cash_arr, index=close.index, name="cash")

    returns = np.diff(equity_arr) / equity_arr[:-1]
    returns = returns[np.isfinite(returns)]

    if len(returns) > 1 and equity_arr[0] > 0:
        years = n / ppy
        cagr = float((equity_arr[-1] / equity_arr[0]) ** (1.0 / max(years, 1e-9)) - 1.0)
    else:
        cagr = 0.0
    ann_vol = float(returns.std(ddof=1) * np.sqrt(ppy)) if len(returns) > 1 else 0.0
    mdd = _max_drawdown(equity_arr)
    sharpe = _sharpe(returns, ppy)
    sortino = _sortino(returns, ppy)

    logger.info(
        "Demon backtest: %d rebalances, CAGR=%.3f vol=%.3f MDD=%.3f Sharpe=%.2f",
        len(rebalance_events), cagr, ann_vol, mdd, sharpe,
    )

    return BacktestResult(
        equity_curve=equity,
        risky_value=risky_s,
        cash_value=cash_s,
        rebalance_events=rebalance_events,
        n_rebalances=len(rebalance_events),
        total_costs=float(total_cost_paid),
        cagr=cagr,
        annualised_vol=ann_vol,
        max_drawdown=mdd,
        sharpe=sharpe,
        sortino=sortino,
        final_value=float(equity_arr[-1]),
    )
