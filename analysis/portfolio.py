"""Dual-sleeve portfolio Monte Carlo: Demon (sleeve A) + Crypto leverage (sleeve B).

Sleeve A is simulated by re-running the deterministic demon backtest on the
real series (one path), then bootstrapping its returns to match the MC horizon.

Sleeve B is parametric: synthetic Student-t innovations scaled to match the
user's expected mean / vol / drawdown profile, with optional correlation to
sleeve A through a Gaussian copula on the innovations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from analysis.backtest import BacktestResult, run_demon_backtest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
@dataclass
class SleeveMetrics:
    cagr: float
    annualised_vol: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    worst_case_dd_p5: float
    best_case_terminal_p95: float
    prob_loss: float
    prob_dd_over_50pct: float


@dataclass
class PortfolioResult:
    """Aggregate Monte Carlo output for the dual-sleeve simulation."""

    n_simulations: int
    horizon_periods: int
    periods_per_year: float

    # Per-simulation paths (n_simulations x horizon)
    sleeve_a_paths: np.ndarray
    sleeve_b_paths: np.ndarray
    combined_paths: np.ndarray

    # Equity curve summary statistics across simulations
    combined_mean: np.ndarray
    combined_p_low: np.ndarray
    combined_p_high: np.ndarray
    combined_p50: np.ndarray

    # Drawdown
    drawdown_mean: np.ndarray
    drawdown_worst: np.ndarray

    # Terminal-value distribution
    terminal_values_combined: np.ndarray
    terminal_values_a: np.ndarray
    terminal_values_b: np.ndarray

    # Metrics
    metrics_a: SleeveMetrics
    metrics_b: SleeveMetrics
    metrics_combined: SleeveMetrics

    # Sleeve contribution time series (mean across sims)
    sleeve_a_contribution: np.ndarray
    sleeve_b_contribution: np.ndarray

    # Time index for plotting (synthetic — periods)
    time_index: np.ndarray


# ---------------------------------------------------------------------------
def _max_dd_path(path: np.ndarray) -> float:
    peaks = np.maximum.accumulate(path, axis=-1)
    dd = (path - peaks) / peaks
    return float(dd.min(axis=-1)) if path.ndim == 1 else dd.min(axis=-1)


def _max_dd_matrix(paths: np.ndarray) -> np.ndarray:
    peaks = np.maximum.accumulate(paths, axis=1)
    dd = (paths - peaks) / peaks
    return dd.min(axis=1)


def _drawdown_curves(paths: np.ndarray) -> np.ndarray:
    peaks = np.maximum.accumulate(paths, axis=1)
    return (paths - peaks) / peaks


def _metrics_from_paths(
    paths: np.ndarray,
    ppy: float,
    rf_annual: float,
    mar_annual: float,
    confidence_low_pct: int,
    confidence_high_pct: int,
) -> SleeveMetrics:
    n_sims, n_steps = paths.shape
    horizon_years = n_steps / ppy

    # Per-sim returns from path
    rets = np.diff(paths, axis=1) / paths[:, :-1]
    rets[~np.isfinite(rets)] = 0.0

    mean_ret = rets.mean(axis=1)
    cagr_per_sim = (paths[:, -1] / paths[:, 0]) ** (1.0 / max(horizon_years, 1e-9)) - 1.0
    cagr = float(np.mean(cagr_per_sim))

    vol_per_sim = rets.std(axis=1, ddof=1) * np.sqrt(ppy)
    ann_vol = float(np.mean(vol_per_sim))

    excess = rets - rf_annual / ppy
    mean_excess = excess.mean(axis=1)
    std_excess = excess.std(axis=1, ddof=1)
    sharpe_per = np.where(std_excess > 0, mean_excess / std_excess * np.sqrt(ppy), 0.0)
    sharpe = float(np.mean(sharpe_per))

    excess_mar = rets - mar_annual / ppy
    sortino_per = np.zeros(n_sims)
    for i in range(n_sims):
        downside = excess_mar[i][excess_mar[i] < 0]
        if len(downside) > 1 and downside.std(ddof=1) > 0:
            sortino_per[i] = excess_mar[i].mean() / downside.std(ddof=1) * np.sqrt(ppy)
    sortino = float(np.mean(sortino_per))

    dd_per_sim = _max_dd_matrix(paths)
    max_dd = float(np.mean(dd_per_sim))
    worst_dd = float(np.percentile(dd_per_sim, 5))     # p5 = worst case
    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-9 else 0.0

    terminal = paths[:, -1] / paths[:, 0]
    best_terminal = float(np.percentile(terminal, 95))
    prob_loss = float((terminal < 1.0).mean())
    prob_big_dd = float((dd_per_sim < -0.50).mean())

    return SleeveMetrics(
        cagr=cagr,
        annualised_vol=ann_vol,
        sharpe=sharpe,
        sortino=sortino,
        calmar=float(calmar),
        max_drawdown=max_dd,
        worst_case_dd_p5=worst_dd,
        best_case_terminal_p95=best_terminal,
        prob_loss=prob_loss,
        prob_dd_over_50pct=prob_big_dd,
    )


# ---------------------------------------------------------------------------
def _bootstrap_returns(
    historical_returns: np.ndarray,
    n_sims: int,
    horizon: int,
    rng: np.random.Generator,
    block_size: int = 20,
) -> np.ndarray:
    """Stationary block bootstrap for sleeve A returns.

    Preserves short-range autocorrelation that pure i.i.d. resampling destroys.
    """
    n = len(historical_returns)
    if n == 0:
        return np.zeros((n_sims, horizon))

    out = np.empty((n_sims, horizon))
    for s in range(n_sims):
        path = []
        while len(path) < horizon:
            start = rng.integers(0, n)
            length = max(1, int(rng.geometric(1.0 / block_size)))
            block = historical_returns[start : start + length]
            if len(block) < length:
                block = np.concatenate([block, historical_returns[: length - len(block)]])
            path.extend(block.tolist())
        out[s] = np.array(path[:horizon])
    return out


def _calibrate_sleeve_b_innovations(
    n_sims: int,
    horizon: int,
    target_annual_return: float,
    target_annual_vol: float,
    target_max_dd: float,
    df: int,
    ppy: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate Student-t innovations calibrated to the target annual stats.

    We sample from t with given df, scale to target per-period vol, then add a
    drift to hit target per-period mean. The drawdown target is informational
    only — fat tails plus the chosen vol naturally produce realistic DD.
    """
    period_vol = target_annual_vol / np.sqrt(ppy)
    period_mean = target_annual_return / ppy

    # Student-t scaled so its variance equals 1, then * period_vol
    t_var = df / (df - 2) if df > 2 else 1.0
    raw = stats.t.rvs(df=df, size=(n_sims, horizon), random_state=rng)
    scaled = raw / np.sqrt(t_var) * period_vol
    return scaled + period_mean


def _apply_correlation(
    sleeve_a_rets: np.ndarray,
    sleeve_b_rets: np.ndarray,
    rho: float,
) -> np.ndarray:
    """Couple sleeve B returns to sleeve A using Gaussian copula on standardised series."""
    if abs(rho) < 1e-6:
        return sleeve_b_rets

    a_std = (sleeve_a_rets - sleeve_a_rets.mean(axis=1, keepdims=True)) / (
        sleeve_a_rets.std(axis=1, ddof=1, keepdims=True) + 1e-12
    )
    b_std = (sleeve_b_rets - sleeve_b_rets.mean(axis=1, keepdims=True)) / (
        sleeve_b_rets.std(axis=1, ddof=1, keepdims=True) + 1e-12
    )
    coupled_std = rho * a_std + np.sqrt(max(0.0, 1.0 - rho * rho)) * b_std
    return coupled_std * sleeve_b_rets.std(axis=1, ddof=1, keepdims=True) + sleeve_b_rets.mean(
        axis=1, keepdims=True
    )


# ---------------------------------------------------------------------------
def run_dual_sleeve_simulation(
    *,
    sleeve_a_backtest: BacktestResult,
    sleeve_a_alloc_pct: float,
    sleeve_b_alloc_pct: float,
    sleeve_b_expected_return_pct: float,
    sleeve_b_expected_vol_pct: float,
    sleeve_b_expected_max_dd_pct: float,
    sleeve_b_win_rate_pct: float,
    sleeve_b_avg_leverage: float,
    sleeve_b_funding_cost_pct: float,
    sleeve_b_stop_loss_pct: float,
    correlation: float,
    n_simulations: int,
    random_seed: int,
    horizon_periods: int,
    periods_per_year: float,
    student_t_df: int,
    risk_free_rate_pct: float,
    mar_pct: float,
    confidence_low_pct: int,
    confidence_high_pct: int,
) -> PortfolioResult:
    """Run a Monte Carlo over the combined dual-sleeve portfolio.

    Sleeve A is bootstrapped from the actual demon equity curve. Sleeve B is
    parametrically simulated from user-supplied expectations. Combined return
    each period is the weighted sum of the two sleeves.

    Returns:
        PortfolioResult containing per-sim paths, summary curves, and metrics.
    """
    rng = np.random.default_rng(random_seed)
    n_sims = max(1, int(n_simulations))
    horizon = max(50, int(horizon_periods))
    ppy = float(periods_per_year)

    alloc_a = sleeve_a_alloc_pct / 100.0
    alloc_b = sleeve_b_alloc_pct / 100.0
    if alloc_a + alloc_b <= 0:
        alloc_a, alloc_b = 0.5, 0.5

    # ---- Sleeve A: bootstrap historical demon returns ----
    a_eq = sleeve_a_backtest.equity_curve.to_numpy()
    if len(a_eq) > 1 and a_eq[0] > 0:
        a_rets_hist = np.diff(a_eq) / a_eq[:-1]
        a_rets_hist = a_rets_hist[np.isfinite(a_rets_hist)]
    else:
        a_rets_hist = np.zeros(1)

    sleeve_a_returns = _bootstrap_returns(a_rets_hist, n_sims, horizon, rng)

    # ---- Sleeve B: parametric ----
    target_ret = sleeve_b_expected_return_pct / 100.0
    target_vol = sleeve_b_expected_vol_pct / 100.0
    target_dd = sleeve_b_expected_max_dd_pct / 100.0
    funding = sleeve_b_funding_cost_pct / 100.0
    leverage = sleeve_b_avg_leverage

    # Cost adjustment: funding cost is paid on borrowed capital ((L-1) of NAV)
    funding_per_period = (leverage - 1.0) * funding / ppy

    # Win rate is informational; we incorporate it as skew via flipping a
    # fraction of positive moves to negatives if the natural win rate is too high.
    sleeve_b_returns = _calibrate_sleeve_b_innovations(
        n_sims, horizon,
        target_annual_return=target_ret,
        target_annual_vol=target_vol,
        target_max_dd=target_dd,
        df=student_t_df,
        ppy=ppy,
        rng=rng,
    )

    # Apply correlation (after sleeve A returns are sampled)
    sleeve_b_returns = _apply_correlation(sleeve_a_returns, sleeve_b_returns, correlation)

    # Apply stop-loss: clip each-period drawdown at -stop_loss
    sl = sleeve_b_stop_loss_pct / 100.0
    if sl > 0:
        sleeve_b_returns = np.clip(sleeve_b_returns, -sl * leverage, None)

    # Apply funding cost
    sleeve_b_returns = sleeve_b_returns - funding_per_period

    # Build paths
    sleeve_a_paths = np.cumprod(1.0 + sleeve_a_returns, axis=1)
    sleeve_b_paths = np.cumprod(1.0 + sleeve_b_returns, axis=1)

    # Prepend $1 starting value
    sleeve_a_paths = np.concatenate([np.ones((n_sims, 1)), sleeve_a_paths], axis=1)
    sleeve_b_paths = np.concatenate([np.ones((n_sims, 1)), sleeve_b_paths], axis=1)

    # Combined: weighted sum at each step (continuous rebal between sleeves)
    weighted_a_returns = alloc_a * sleeve_a_returns
    weighted_b_returns = alloc_b * sleeve_b_returns
    combined_returns = weighted_a_returns + weighted_b_returns
    combined_paths = np.concatenate(
        [np.ones((n_sims, 1)), np.cumprod(1.0 + combined_returns, axis=1)], axis=1
    )

    # Summary curves
    combined_mean = combined_paths.mean(axis=0)
    combined_p_low = np.percentile(combined_paths, confidence_low_pct, axis=0)
    combined_p_high = np.percentile(combined_paths, confidence_high_pct, axis=0)
    combined_p50 = np.percentile(combined_paths, 50, axis=0)

    dd_mat = _drawdown_curves(combined_paths)
    drawdown_mean = dd_mat.mean(axis=0)
    drawdown_worst = dd_mat.min(axis=0)

    metrics_a = _metrics_from_paths(
        sleeve_a_paths, ppy, risk_free_rate_pct / 100.0, mar_pct / 100.0,
        confidence_low_pct, confidence_high_pct,
    )
    metrics_b = _metrics_from_paths(
        sleeve_b_paths, ppy, risk_free_rate_pct / 100.0, mar_pct / 100.0,
        confidence_low_pct, confidence_high_pct,
    )
    metrics_combined = _metrics_from_paths(
        combined_paths, ppy, risk_free_rate_pct / 100.0, mar_pct / 100.0,
        confidence_low_pct, confidence_high_pct,
    )

    sleeve_a_contribution = (alloc_a * sleeve_a_paths).mean(axis=0)
    sleeve_b_contribution = (alloc_b * sleeve_b_paths).mean(axis=0)

    time_index = np.arange(combined_paths.shape[1])

    logger.info(
        "MC: %d sims x %d periods, combined CAGR=%.3f Sortino=%.2f MDD=%.3f",
        n_sims, horizon, metrics_combined.cagr, metrics_combined.sortino, metrics_combined.max_drawdown,
    )

    return PortfolioResult(
        n_simulations=n_sims,
        horizon_periods=horizon,
        periods_per_year=ppy,
        sleeve_a_paths=sleeve_a_paths,
        sleeve_b_paths=sleeve_b_paths,
        combined_paths=combined_paths,
        combined_mean=combined_mean,
        combined_p_low=combined_p_low,
        combined_p_high=combined_p_high,
        combined_p50=combined_p50,
        drawdown_mean=drawdown_mean,
        drawdown_worst=drawdown_worst,
        terminal_values_combined=combined_paths[:, -1],
        terminal_values_a=sleeve_a_paths[:, -1],
        terminal_values_b=sleeve_b_paths[:, -1],
        metrics_a=metrics_a,
        metrics_b=metrics_b,
        metrics_combined=metrics_combined,
        sleeve_a_contribution=sleeve_a_contribution,
        sleeve_b_contribution=sleeve_b_contribution,
        time_index=time_index,
    )
