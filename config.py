"""Centralised configuration: thresholds, defaults, and constants.

All magic numbers live here so the rest of the codebase can be tuned without
hunting through files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final


# ---------------------------------------------------------------------------
# Data validation thresholds
# ---------------------------------------------------------------------------
MIN_OBS_HARD_BLOCK: Final[int] = 50
MIN_OBS_SOFT_WARN: Final[int] = 250
GAP_WARN_MULTIPLIER: Final[float] = 5.0


# ---------------------------------------------------------------------------
# Statistical test thresholds
# ---------------------------------------------------------------------------
ADF_PASS_PVALUE: Final[float] = 0.05
ADF_MARGINAL_PVALUE: Final[float] = 0.10
KPSS_PASS_PVALUE: Final[float] = 0.05

HURST_MEAN_REVERTING_MAX: Final[float] = 0.45
HURST_RANDOM_WALK_MAX: Final[float] = 0.55
HURST_DIVERGENCE_THRESHOLD: Final[float] = 0.10

HALF_LIFE_BETA_MAX_PVALUE: Final[float] = 0.05

# Volatility guidance bands (annualised, decimal form)
VOL_LOW_BAND: Final[float] = 0.05
VOL_HIGH_BAND: Final[float] = 0.30

# Regime detection
REGIME_ROLLING_WINDOW: Final[int] = 90
REGIME_DETECTION_WINDOW: Final[int] = 30
REGIME_SHIFT_THRESHOLD_SIGMA: Final[float] = 2.0


# ---------------------------------------------------------------------------
# Suitability scoring (0-100 with verdict bands)
# ---------------------------------------------------------------------------
VERDICT_STRONG_MIN: Final[int] = 80
VERDICT_MARGINAL_MIN: Final[int] = 60
VERDICT_WEAK_MIN: Final[int] = 40

SCORE_WEIGHTS: Final[dict[str, int]] = {
    "adf": 20,
    "kpss": 15,
    "hurst": 20,
    "half_life": 15,
    "vol_band": 15,
    "regime_stability": 15,
}


# ---------------------------------------------------------------------------
# Calendar / annualisation defaults
# ---------------------------------------------------------------------------
DEFAULT_TRADING_DAYS_PER_YEAR: Final[int] = 252
CRYPTO_DAYS_PER_YEAR: Final[int] = 365
DEFAULT_TRADING_HOURS_PER_YEAR: Final[int] = 6048   # 252 * 24
CALENDAR_HOURS_PER_YEAR: Final[int] = 8760


# ---------------------------------------------------------------------------
# Sleeve A (Shannon's Demon) defaults
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SleeveADefaults:
    capital_alloc_pct: float = 50.0          # % of portfolio
    demon_weight: float = 0.5                # risky-asset weight inside sleeve
    rebalance_rule: str = "time"             # "time" | "threshold" | "band"
    time_rebalance_periods: int = 24         # fallback if half-life undefined
    threshold_drift_pct: float = 10.0        # ± from target weight
    band_sigma: float = 1.0
    cash_yield_pct: float = 0.0              # %/year
    transaction_cost_bps: float = 5.0        # bps per rebalance


# ---------------------------------------------------------------------------
# Sleeve B (Crypto Leverage) defaults
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SleeveBDefaults:
    expected_annual_return_pct: float = 40.0
    expected_annual_vol_pct: float = 80.0
    expected_max_drawdown_pct: float = 35.0
    win_rate_pct: float = 45.0
    avg_leverage: float = 5.0
    funding_cost_pct: float = 10.0           # %/year borrow
    stop_loss_pct: float = 2.0               # per trade
    correlation_with_a: float = 0.0
    student_t_df: int = 4                    # fat-tail parameter


# ---------------------------------------------------------------------------
# Monte Carlo / sidebar power-user
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MonteCarloDefaults:
    n_simulations: int = 1_000
    n_simulations_min: int = 100
    n_simulations_max: int = 10_000
    random_seed: int = 42
    risk_free_rate_pct: float = 4.0
    mar_pct: float = 0.0                     # min acceptable return for Sortino
    confidence_low: int = 10
    confidence_high: int = 90


# ---------------------------------------------------------------------------
# Leverage sensitivity
# ---------------------------------------------------------------------------
LEVERAGE_MIN: Final[float] = 1.0
LEVERAGE_MAX: Final[float] = 5.0
LEVERAGE_STEP: Final[float] = 0.25
LEVERAGE_DD_RED_THRESHOLD: Final[float] = 0.30
LEVERAGE_MARGIN_CALL_DD: Final[float] = 0.50


# ---------------------------------------------------------------------------
# Allocation optimiser sweep
# ---------------------------------------------------------------------------
ALLOC_SWEEP_STEP_PCT: Final[float] = 5.0


SLEEVE_A_DEFAULTS: Final[SleeveADefaults] = SleeveADefaults()
SLEEVE_B_DEFAULTS: Final[SleeveBDefaults] = SleeveBDefaults()
MC_DEFAULTS: Final[MonteCarloDefaults] = MonteCarloDefaults()


# ---------------------------------------------------------------------------
# Theme — quant / institutional dark palette
# ---------------------------------------------------------------------------
THEME_BG: Final[str] = "#0B0E11"             # page
THEME_CARD: Final[str] = "#11151B"           # surface
THEME_CARD_ALT: Final[str] = "#161B22"
THEME_BORDER: Final[str] = "#21262D"
THEME_GRID: Final[str] = "#1B2028"
THEME_TEXT: Final[str] = "#E6EDF3"
THEME_TEXT_MUTED: Final[str] = "#8B949E"
THEME_ACCENT: Final[str] = "#C8A24A"          # muted gold
THEME_SUCCESS: Final[str] = "#3FB950"
THEME_WARNING: Final[str] = "#D29922"
THEME_DANGER: Final[str] = "#DA3633"
THEME_INFO: Final[str] = "#58A6FF"
THEME_PURPLE: Final[str] = "#A371F7"
THEME_TEAL: Final[str] = "#39B3B8"

# Plotly layout defaults to apply to every figure
PLOTLY_DEFAULTS: Final[dict] = {
    "paper_bgcolor": THEME_CARD,
    "plot_bgcolor": THEME_BG,
    "font": {"color": THEME_TEXT, "family": "Inter, -apple-system, Segoe UI, sans-serif", "size": 12},
    "colorway": [THEME_ACCENT, THEME_INFO, THEME_TEAL, THEME_PURPLE, THEME_SUCCESS, THEME_WARNING, THEME_DANGER],
    "xaxis": {"gridcolor": THEME_GRID, "zerolinecolor": THEME_BORDER, "linecolor": THEME_BORDER},
    "yaxis": {"gridcolor": THEME_GRID, "zerolinecolor": THEME_BORDER, "linecolor": THEME_BORDER},
    "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"color": THEME_TEXT}},
    "hoverlabel": {"bgcolor": THEME_CARD_ALT, "font": {"color": THEME_TEXT}, "bordercolor": THEME_BORDER},
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL: Final[str] = "INFO"
