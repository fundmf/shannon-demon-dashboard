"""Statistical tests for mean-reversion suitability.

Each test returns a typed dataclass with raw output, status badge string,
and any auxiliary data the UI layer needs to render charts.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

import config as cfg

logger = logging.getLogger(__name__)


Status = Literal["pass", "marginal", "fail", "error"]


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ADFResult:
    """Augmented Dickey-Fuller test output for both 'c' and 'ct' specs."""

    statistic_c: float
    pvalue_c: float
    used_lag_c: int
    critical_values_c: dict[str, float]

    statistic_ct: float
    pvalue_ct: float
    used_lag_ct: int
    critical_values_ct: dict[str, float]

    status: Status
    error: Optional[str] = None


@dataclass
class KPSSResult:
    statistic: float
    pvalue: float
    used_lag: int
    critical_values: dict[str, float]
    boundary_warning: bool
    status: Status
    error: Optional[str] = None


@dataclass
class HurstResult:
    rs_hurst: float
    var_hurst: float
    inconsistent: bool
    status: Status
    rs_log_n: list[float] = field(default_factory=list)
    rs_log_rs: list[float] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def best_estimate(self) -> float:
        """Average of the two estimates if consistent, else R/S as anchor."""
        if self.inconsistent:
            return self.rs_hurst
        return float(np.mean([self.rs_hurst, self.var_hurst]))


@dataclass
class HalfLifeResult:
    beta: float
    beta_pvalue: float
    half_life_periods: float            # NaN if undefined
    half_life_human: str
    suggested_rebalance_min_periods: float
    suggested_rebalance_max_periods: float
    status: Status
    error: Optional[str] = None


@dataclass
class RegimeResult:
    rolling_mean: pd.Series
    rolling_std: pd.Series
    expanding_mean: pd.Series
    shift_indices: list[int]
    n_shifts: int
    method: str            # "heuristic" | "pelt"
    status: Status
    error: Optional[str] = None


@dataclass
class VolatilityResult:
    full_sample_annualised: float
    realised_30p_annualised: float
    log_returns: pd.Series
    rolling_30p_annualised: pd.Series
    periods_per_year: float
    status: Status
    error: Optional[str] = None


@dataclass
class HarvestResult:
    weight: float
    annual_variance: float
    bonus_pct: float
    curve_w: np.ndarray
    curve_bonus: np.ndarray


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _series_is_valid(s: pd.Series, min_n: int = 20) -> Optional[str]:
    """Return error string if series is unusable, else None."""
    if s is None or len(s) < min_n:
        return f"series has only {len(s) if s is not None else 0} obs (need >= {min_n})"
    if s.isna().any():
        return "series contains NaN values"
    if not np.isfinite(s.to_numpy()).all():
        return "series contains inf values"
    if s.nunique() < 3:
        return "series is constant or near-constant"
    return None


def _to_numpy(s: pd.Series) -> np.ndarray:
    return np.asarray(s.dropna(), dtype=float)


# ---------------------------------------------------------------------------
# 1. ADF
# ---------------------------------------------------------------------------
def run_adf(close: pd.Series) -> ADFResult:
    """Run ADF test under both 'c' and 'ct' regression specifications.

    Args:
        close: cleaned close-price series.

    Returns:
        ADFResult with both spec outputs and a combined status badge.
    """
    err = _series_is_valid(close)
    if err is not None:
        logger.warning("ADF skipped: %s", err)
        return ADFResult(
            statistic_c=np.nan, pvalue_c=np.nan, used_lag_c=0, critical_values_c={},
            statistic_ct=np.nan, pvalue_ct=np.nan, used_lag_ct=0, critical_values_ct={},
            status="error", error=err,
        )

    try:
        x = _to_numpy(close)
        c_stat, c_p, c_lag, c_n, c_crit, _ = adfuller(x, regression="c", autolag="AIC")
        ct_stat, ct_p, ct_lag, ct_n, ct_crit, _ = adfuller(x, regression="ct", autolag="AIC")

        if c_p < cfg.ADF_PASS_PVALUE:
            status: Status = "pass"
        elif c_p < cfg.ADF_MARGINAL_PVALUE:
            status = "marginal"
        else:
            status = "fail"

        logger.info("ADF: c p=%.4f ct p=%.4f -> %s", c_p, ct_p, status)

        return ADFResult(
            statistic_c=float(c_stat),
            pvalue_c=float(c_p),
            used_lag_c=int(c_lag),
            critical_values_c={k: float(v) for k, v in c_crit.items()},
            statistic_ct=float(ct_stat),
            pvalue_ct=float(ct_p),
            used_lag_ct=int(ct_lag),
            critical_values_ct={k: float(v) for k, v in ct_crit.items()},
            status=status,
        )
    except Exception as e:
        logger.exception("ADF failed")
        return ADFResult(
            statistic_c=np.nan, pvalue_c=np.nan, used_lag_c=0, critical_values_c={},
            statistic_ct=np.nan, pvalue_ct=np.nan, used_lag_ct=0, critical_values_ct={},
            status="error", error=str(e),
        )


# ---------------------------------------------------------------------------
# 2. KPSS
# ---------------------------------------------------------------------------
def run_kpss(close: pd.Series) -> KPSSResult:
    """KPSS level-stationarity test."""
    err = _series_is_valid(close)
    if err is not None:
        return KPSSResult(
            statistic=np.nan, pvalue=np.nan, used_lag=0, critical_values={},
            boundary_warning=False, status="error", error=err,
        )

    try:
        x = _to_numpy(close)
        boundary = False
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always", InterpolationWarning)
            stat, pval, lag, crit = kpss(x, regression="c", nlags="auto")
            for w in wlist:
                if issubclass(w.category, InterpolationWarning):
                    boundary = True

        status: Status = "pass" if pval > cfg.KPSS_PASS_PVALUE else "fail"
        logger.info("KPSS: stat=%.3f p=%.4f -> %s", stat, pval, status)

        return KPSSResult(
            statistic=float(stat),
            pvalue=float(pval),
            used_lag=int(lag),
            critical_values={k: float(v) for k, v in crit.items()},
            boundary_warning=boundary,
            status=status,
        )
    except Exception as e:
        logger.exception("KPSS failed")
        return KPSSResult(
            statistic=np.nan, pvalue=np.nan, used_lag=0, critical_values={},
            boundary_warning=False, status="error", error=str(e),
        )


# ---------------------------------------------------------------------------
# 3. Hurst
# ---------------------------------------------------------------------------
def _rs_hurst(x: np.ndarray) -> tuple[float, list[float], list[float]]:
    """Manual rescaled-range Hurst estimator.

    Returns (H, log_n_points, log_rs_points) for plotting.
    """
    n = len(x)
    if n < 30:
        return float("nan"), [], []

    min_w = max(10, n // 20)
    max_w = max(min_w + 1, n // 2)
    # Log-spaced window sizes
    sizes = np.unique(
        np.floor(np.logspace(np.log10(min_w), np.log10(max_w), num=20)).astype(int)
    )

    rs_values = []
    log_n = []
    for w in sizes:
        if w < 10 or w >= n:
            continue
        n_chunks = n // w
        if n_chunks < 1:
            continue
        rs_chunk = []
        for k in range(n_chunks):
            chunk = x[k * w : (k + 1) * w]
            mean = chunk.mean()
            dev = chunk - mean
            cum_dev = np.cumsum(dev)
            R = cum_dev.max() - cum_dev.min()
            S = chunk.std(ddof=1)
            if S > 0:
                rs_chunk.append(R / S)
        if rs_chunk:
            rs_values.append(np.mean(rs_chunk))
            log_n.append(np.log(w))
    if len(rs_values) < 4:
        return float("nan"), [], []

    log_rs = np.log(rs_values)
    log_n_arr = np.array(log_n)
    slope, _, _, _, _ = stats.linregress(log_n_arr, log_rs)
    return float(slope), log_n_arr.tolist(), log_rs.tolist()


def _variance_hurst(x: np.ndarray, max_lag: int = 100) -> float:
    """Hurst via variance of lagged increments. H = slope/2 of log-log fit."""
    n = len(x)
    max_lag = max(2, min(max_lag, n // 4))
    lags = np.unique(np.floor(np.logspace(0, np.log10(max_lag), num=15)).astype(int))
    lags = lags[lags >= 1]

    log_var = []
    log_lag = []
    for tau in lags:
        diffs = x[tau:] - x[:-tau]
        v = np.var(diffs, ddof=1)
        if v > 0:
            log_var.append(np.log(v))
            log_lag.append(np.log(tau))
    if len(log_var) < 4:
        return float("nan")
    slope, _, _, _, _ = stats.linregress(log_lag, log_var)
    return float(slope / 2.0)


def run_hurst(close: pd.Series) -> HurstResult:
    """Compute Hurst via R/S and variance methods; flag inconsistency."""
    err = _series_is_valid(close, min_n=60)
    if err is not None:
        return HurstResult(
            rs_hurst=np.nan, var_hurst=np.nan, inconsistent=False,
            status="error", error=err,
        )

    try:
        x = _to_numpy(close)
        rs_h, log_n, log_rs = _rs_hurst(x)
        var_h = _variance_hurst(x)

        if not np.isfinite(rs_h) or not np.isfinite(var_h):
            return HurstResult(
                rs_hurst=float(rs_h) if np.isfinite(rs_h) else np.nan,
                var_hurst=float(var_h) if np.isfinite(var_h) else np.nan,
                inconsistent=True, status="error",
                error="Hurst estimation failed",
            )

        inconsistent = abs(rs_h - var_h) > cfg.HURST_DIVERGENCE_THRESHOLD
        best = (rs_h + var_h) / 2.0

        if best < cfg.HURST_MEAN_REVERTING_MAX:
            status: Status = "pass"
        elif best <= cfg.HURST_RANDOM_WALK_MAX:
            status = "marginal"
        else:
            status = "fail"

        logger.info("Hurst: R/S=%.3f Var=%.3f -> %s", rs_h, var_h, status)

        return HurstResult(
            rs_hurst=float(rs_h),
            var_hurst=float(var_h),
            inconsistent=bool(inconsistent),
            status=status,
            rs_log_n=log_n,
            rs_log_rs=log_rs,
        )
    except Exception as e:
        logger.exception("Hurst failed")
        return HurstResult(
            rs_hurst=np.nan, var_hurst=np.nan, inconsistent=False,
            status="error", error=str(e),
        )


# ---------------------------------------------------------------------------
# 4. Half-Life
# ---------------------------------------------------------------------------
def _humanise_periods(n_periods: float, interval: pd.Timedelta) -> str:
    """Convert a count of periods into a human-readable duration."""
    if not np.isfinite(n_periods) or n_periods <= 0:
        return "undefined"
    seconds = n_periods * interval.total_seconds()
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"
    hours = minutes / 60
    if hours < 48:
        return f"{hours:.1f} hours"
    days = hours / 24
    if days < 60:
        return f"{days:.1f} days"
    weeks = days / 7
    if weeks < 12:
        return f"{weeks:.1f} weeks"
    return f"{days/30.4375:.1f} months"


def run_half_life(close: pd.Series, interval: pd.Timedelta) -> HalfLifeResult:
    """Estimate AR(1) half-life of mean reversion via OLS.

    Δs_t = α + β · s_{t-1} + ε
    half_life = -ln(2) / ln(1 + β)   (defined when -1 < β < 0)
    """
    err = _series_is_valid(close, min_n=30)
    if err is not None:
        return HalfLifeResult(
            beta=np.nan, beta_pvalue=np.nan, half_life_periods=np.nan,
            half_life_human="undefined",
            suggested_rebalance_min_periods=np.nan,
            suggested_rebalance_max_periods=np.nan,
            status="error", error=err,
        )

    try:
        x = _to_numpy(close)
        lagged = x[:-1]
        delta = np.diff(x)
        X = np.column_stack([np.ones_like(lagged), lagged])
        model = OLS(delta, X).fit()
        alpha, beta = float(model.params[0]), float(model.params[1])
        beta_p = float(model.pvalues[1])

        if -1 < beta < 0:
            hl = -np.log(2) / np.log(1 + beta)
        else:
            hl = float("nan")

        if (
            np.isfinite(hl)
            and hl > 0
            and beta_p < cfg.HALF_LIFE_BETA_MAX_PVALUE
        ):
            status: Status = "pass"
        elif np.isfinite(hl) and hl > 0:
            status = "marginal"
        else:
            status = "fail"

        human = _humanise_periods(hl, interval)
        rb_min = 0.5 * hl if np.isfinite(hl) else np.nan
        rb_max = 1.0 * hl if np.isfinite(hl) else np.nan

        logger.info(
            "Half-life: beta=%.5f p=%.4f hl=%.2f periods (%s) -> %s",
            beta, beta_p, hl if np.isfinite(hl) else -1, human, status,
        )

        return HalfLifeResult(
            beta=beta,
            beta_pvalue=beta_p,
            half_life_periods=float(hl) if np.isfinite(hl) else np.nan,
            half_life_human=human,
            suggested_rebalance_min_periods=float(rb_min) if np.isfinite(rb_min) else np.nan,
            suggested_rebalance_max_periods=float(rb_max) if np.isfinite(rb_max) else np.nan,
            status=status,
        )
    except Exception as e:
        logger.exception("Half-life failed")
        return HalfLifeResult(
            beta=np.nan, beta_pvalue=np.nan, half_life_periods=np.nan,
            half_life_human="undefined",
            suggested_rebalance_min_periods=np.nan,
            suggested_rebalance_max_periods=np.nan,
            status="error", error=str(e),
        )


# ---------------------------------------------------------------------------
# 5. Regime detection
# ---------------------------------------------------------------------------
def run_regime_detection(close: pd.Series) -> RegimeResult:
    """Rolling-window regime stability with optional ruptures backend."""
    err = _series_is_valid(close, min_n=cfg.REGIME_ROLLING_WINDOW + 10)
    if err is not None:
        empty = pd.Series(dtype=float)
        return RegimeResult(
            rolling_mean=empty, rolling_std=empty, expanding_mean=empty,
            shift_indices=[], n_shifts=0, method="none",
            status="error", error=err,
        )

    try:
        rolling_mean = close.rolling(cfg.REGIME_ROLLING_WINDOW).mean()
        rolling_std = close.rolling(cfg.REGIME_ROLLING_WINDOW).std()
        expanding_mean = close.expanding(min_periods=cfg.REGIME_ROLLING_WINDOW).mean()

        # Heuristic: 30p rolling means moving > 2σ_long apart
        long_std = float(close.std(ddof=1))
        roll30 = close.rolling(cfg.REGIME_DETECTION_WINDOW).mean()
        prev30 = roll30.shift(cfg.REGIME_DETECTION_WINDOW)
        diff = (roll30 - prev30).abs()
        threshold = cfg.REGIME_SHIFT_THRESHOLD_SIGMA * long_std
        candidates = diff[diff > threshold].index.tolist()

        # Suppress nearby duplicates (within window)
        shift_indices: list[int] = []
        last_idx = -10**9
        for idx in candidates:
            i = close.index.get_loc(idx)
            if i - last_idx > cfg.REGIME_DETECTION_WINDOW:
                shift_indices.append(int(i))
                last_idx = i

        method = "heuristic"
        try:
            import ruptures as rpt
            algo = rpt.Pelt(model="rbf").fit(close.to_numpy())
            pen = max(1.0, 3.0 * np.log(len(close)) * (long_std ** 2))
            bkps = algo.predict(pen=pen)
            # ruptures returns end indices; drop the final n
            rpt_shifts = [b for b in bkps if b < len(close)]
            if rpt_shifts:
                shift_indices = rpt_shifts
                method = "pelt"
        except Exception:
            logger.info("ruptures unavailable, using heuristic")

        n_shifts = len(shift_indices)
        # Status: 0-1 shifts pass, 2-4 marginal, >4 fail
        if n_shifts <= 1:
            status: Status = "pass"
        elif n_shifts <= 4:
            status = "marginal"
        else:
            status = "fail"

        logger.info("Regime: %d shifts via %s -> %s", n_shifts, method, status)

        return RegimeResult(
            rolling_mean=rolling_mean,
            rolling_std=rolling_std,
            expanding_mean=expanding_mean,
            shift_indices=shift_indices,
            n_shifts=n_shifts,
            method=method,
            status=status,
        )
    except Exception as e:
        logger.exception("Regime detection failed")
        empty = pd.Series(dtype=float)
        return RegimeResult(
            rolling_mean=empty, rolling_std=empty, expanding_mean=empty,
            shift_indices=[], n_shifts=0, method="none",
            status="error", error=str(e),
        )


# ---------------------------------------------------------------------------
# 6. Volatility
# ---------------------------------------------------------------------------
def run_volatility(
    close: pd.Series,
    interval: pd.Timedelta,
    annualisation: str = "trading",
) -> VolatilityResult:
    """Annualised realised vol via log returns.

    Args:
        close: price series.
        interval: median sampling interval (pd.Timedelta).
        annualisation: 'trading' or 'calendar' — controls periods_per_year.
    """
    err = _series_is_valid(close, min_n=30)
    if err is not None:
        empty = pd.Series(dtype=float)
        return VolatilityResult(
            full_sample_annualised=np.nan,
            realised_30p_annualised=np.nan,
            log_returns=empty,
            rolling_30p_annualised=empty,
            periods_per_year=np.nan,
            status="error", error=err,
        )

    try:
        log_ret = np.log(close).diff().dropna()
        seconds = interval.total_seconds()
        if seconds <= 0:
            seconds = 3600.0
        if annualisation == "calendar":
            ppy = (365.25 * 24 * 3600) / seconds
        else:
            # trading hours assumption: ~6048 hours per year (252 * 24)
            ppy = (cfg.DEFAULT_TRADING_HOURS_PER_YEAR * 3600) / seconds

        full_vol = float(log_ret.std(ddof=1) * np.sqrt(ppy))
        last30 = log_ret.tail(30)
        realised30 = float(last30.std(ddof=1) * np.sqrt(ppy)) if len(last30) >= 5 else np.nan
        rolling30 = log_ret.rolling(30).std(ddof=1) * np.sqrt(ppy)

        if cfg.VOL_LOW_BAND <= full_vol <= cfg.VOL_HIGH_BAND:
            status: Status = "pass"
        elif full_vol < cfg.VOL_LOW_BAND or full_vol <= 0.50:
            status = "marginal"
        else:
            status = "fail"

        logger.info("Vol: full=%.3f last30=%.3f ppy=%.1f -> %s",
                    full_vol, realised30 if np.isfinite(realised30) else -1, ppy, status)

        return VolatilityResult(
            full_sample_annualised=full_vol,
            realised_30p_annualised=realised30,
            log_returns=log_ret,
            rolling_30p_annualised=rolling30,
            periods_per_year=float(ppy),
            status=status,
        )
    except Exception as e:
        logger.exception("Volatility failed")
        empty = pd.Series(dtype=float)
        return VolatilityResult(
            full_sample_annualised=np.nan,
            realised_30p_annualised=np.nan,
            log_returns=empty,
            rolling_30p_annualised=empty,
            periods_per_year=np.nan,
            status="error", error=str(e),
        )


# ---------------------------------------------------------------------------
# 7. Shannon Harvest estimator
# ---------------------------------------------------------------------------
def shannon_harvest(weight: float, annual_vol: float) -> HarvestResult:
    """Compute the rebalancing bonus 0.5*w*(1-w)*σ² and the curve over w∈[0,1].

    Args:
        weight: w in the risky asset (0..1).
        annual_vol: annualised stdev of log returns (decimal).
    """
    sigma2 = float(annual_vol) ** 2 if np.isfinite(annual_vol) else 0.0
    bonus = 0.5 * weight * (1 - weight) * sigma2

    grid = np.linspace(0.0, 1.0, 101)
    curve = 0.5 * grid * (1 - grid) * sigma2

    return HarvestResult(
        weight=float(weight),
        annual_variance=float(sigma2),
        bonus_pct=float(bonus * 100),
        curve_w=grid,
        curve_bonus=curve * 100,
    )
