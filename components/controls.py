"""Reusable Streamlit control widgets for both sleeves and the sidebar."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import streamlit as st

import config as cfg


# ---------------------------------------------------------------------------
@dataclass
class SidebarSettings:
    n_simulations: int
    random_seed: int
    trading_days_per_year: int
    risk_free_rate_pct: float
    mar_pct: float
    confidence_low: int
    confidence_high: int
    annualisation: str          # 'trading' | 'calendar'


def render_sidebar() -> SidebarSettings:
    """Render the sidebar power-user controls and return the settings."""
    st.sidebar.header("Power-user parameters")

    if st.sidebar.button("Reset all to defaults", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith(("sb_", "sa_", "sb_b_", "sb_mc_")):
                del st.session_state[k]
        st.rerun()

    n_sims = st.sidebar.slider(
        "Monte Carlo iterations",
        min_value=cfg.MC_DEFAULTS.n_simulations_min,
        max_value=cfg.MC_DEFAULTS.n_simulations_max,
        value=cfg.MC_DEFAULTS.n_simulations,
        step=100,
        key="sb_mc_n",
        help="More iterations = smoother bands, slower compute.",
    )
    seed = st.sidebar.number_input(
        "Random seed", min_value=0, max_value=10**9,
        value=cfg.MC_DEFAULTS.random_seed, step=1, key="sb_mc_seed",
    )

    annual_choice = st.sidebar.radio(
        "Annualisation basis",
        options=["trading", "calendar"],
        index=0,
        format_func=lambda x: "Trading hours (252 d/yr)" if x == "trading" else "Calendar (24/7)",
        key="sb_mc_annual",
        help="Use 'calendar' for 24/7 markets like crypto.",
    )

    days_per_year = st.sidebar.number_input(
        "Trading days per year",
        min_value=200, max_value=370,
        value=cfg.DEFAULT_TRADING_DAYS_PER_YEAR if annual_choice == "trading" else cfg.CRYPTO_DAYS_PER_YEAR,
        step=1, key="sb_mc_dpy",
    )

    rf = st.sidebar.number_input(
        "Risk-free rate (%/yr)",
        min_value=0.0, max_value=20.0,
        value=cfg.MC_DEFAULTS.risk_free_rate_pct, step=0.25,
        key="sb_mc_rf",
    )
    mar = st.sidebar.number_input(
        "MAR for Sortino (%/yr)",
        min_value=-20.0, max_value=50.0,
        value=cfg.MC_DEFAULTS.mar_pct, step=0.25,
        key="sb_mc_mar",
    )

    bands = st.sidebar.radio(
        "Monte Carlo confidence bands",
        options=["10/90", "5/95"], index=0, key="sb_mc_bands",
        help="5/95 is more conservative but noisier.",
    )
    if bands == "10/90":
        low, high = 10, 90
    else:
        low, high = 5, 95

    return SidebarSettings(
        n_simulations=int(n_sims),
        random_seed=int(seed),
        trading_days_per_year=int(days_per_year),
        risk_free_rate_pct=float(rf),
        mar_pct=float(mar),
        confidence_low=int(low),
        confidence_high=int(high),
        annualisation=annual_choice,
    )


# ---------------------------------------------------------------------------
@dataclass
class SleeveAControls:
    capital_alloc_pct: float
    weight: float
    rebalance_rule: str
    time_period: int
    threshold_pct: float
    band_sigma: float
    band_window: int
    cash_yield_pct: float
    transaction_cost_bps: float


def render_sleeve_a(default_time_period: int) -> SleeveAControls:
    """Sleeve A (Shannon's Demon) controls."""
    d = cfg.SLEEVE_A_DEFAULTS
    st.subheader("Sleeve A — Shannon's Demon (uploaded asset)")

    cap = st.slider(
        "Capital allocation to Sleeve A (%)",
        min_value=0.0, max_value=100.0,
        value=d.capital_alloc_pct, step=1.0, key="sa_cap",
    )
    w = st.slider(
        "Demon weight w (risky / cash)",
        min_value=0.10, max_value=0.90,
        value=d.demon_weight, step=0.05, key="sa_w",
    )
    rule = st.radio(
        "Rebalance rule",
        options=["time", "threshold", "band"],
        index=0,
        format_func={"time": "Time-based", "threshold": "Weight-drift threshold",
                     "band": "Band (σ from rolling mean)"}.get,
        key="sa_rule",
    )

    if rule == "time":
        period = st.number_input(
            "Rebalance every N periods",
            min_value=1, max_value=10_000,
            value=int(default_time_period), step=1, key="sa_period",
            help=f"Default = 0.75 × half-life ({default_time_period} periods).",
        )
        threshold = d.threshold_drift_pct
        band_s = d.band_sigma
    elif rule == "threshold":
        threshold = st.slider(
            "Drift threshold (%)",
            min_value=1.0, max_value=50.0,
            value=d.threshold_drift_pct, step=0.5, key="sa_threshold",
        )
        period = default_time_period
        band_s = d.band_sigma
    else:
        band_s = st.slider(
            "Band size (σ from rolling mean)",
            min_value=0.25, max_value=4.0,
            value=d.band_sigma, step=0.25, key="sa_band",
        )
        period = default_time_period
        threshold = d.threshold_drift_pct

    band_window = st.number_input(
        "Rolling window for band rule (periods)",
        min_value=20, max_value=2000, value=90, step=10, key="sa_band_window",
    )

    cash_y = st.number_input(
        "Cash yield (%/yr)",
        min_value=0.0, max_value=15.0, value=d.cash_yield_pct, step=0.25,
        key="sa_cashy",
    )
    tcost = st.number_input(
        "Transaction cost (bps per rebalance)",
        min_value=0.0, max_value=200.0, value=d.transaction_cost_bps, step=1.0,
        key="sa_tcost",
    )

    return SleeveAControls(
        capital_alloc_pct=float(cap),
        weight=float(w),
        rebalance_rule=rule,
        time_period=int(period),
        threshold_pct=float(threshold),
        band_sigma=float(band_s),
        band_window=int(band_window),
        cash_yield_pct=float(cash_y),
        transaction_cost_bps=float(tcost),
    )


# ---------------------------------------------------------------------------
@dataclass
class SleeveBControls:
    capital_alloc_pct: float
    expected_return_pct: float
    expected_vol_pct: float
    expected_max_dd_pct: float
    win_rate_pct: float
    avg_leverage: float
    funding_cost_pct: float
    stop_loss_pct: float
    correlation: float


def render_sleeve_b(sleeve_a_alloc: float) -> SleeveBControls:
    """Sleeve B (Crypto Leverage) controls. Allocation auto-completes Sleeve A."""
    d = cfg.SLEEVE_B_DEFAULTS
    st.subheader("Sleeve B — Crypto leverage trading")

    cap_b = max(0.0, 100.0 - sleeve_a_alloc)
    st.metric("Capital allocation to Sleeve B (%)",
              f"{cap_b:.1f}%",
              help="Auto-complement of Sleeve A. Adjust Sleeve A slider to change.")

    ret = st.number_input(
        "Expected annual return (%)",
        min_value=-50.0, max_value=500.0,
        value=d.expected_annual_return_pct, step=1.0, key="sb_b_ret",
    )
    vol = st.number_input(
        "Expected annual volatility (%)",
        min_value=1.0, max_value=500.0,
        value=d.expected_annual_vol_pct, step=1.0, key="sb_b_vol",
    )
    mdd = st.number_input(
        "Expected max drawdown (%)",
        min_value=1.0, max_value=99.0,
        value=d.expected_max_drawdown_pct, step=1.0, key="sb_b_mdd",
    )
    wr = st.number_input(
        "Win rate (%)",
        min_value=10.0, max_value=90.0,
        value=d.win_rate_pct, step=1.0, key="sb_b_wr",
    )
    lev = st.number_input(
        "Average leverage used",
        min_value=1.0, max_value=20.0,
        value=d.avg_leverage, step=0.5, key="sb_b_lev",
    )
    fund = st.number_input(
        "Funding / borrow cost (%/yr)",
        min_value=0.0, max_value=50.0,
        value=d.funding_cost_pct, step=0.5, key="sb_b_fund",
    )
    sl = st.number_input(
        "Stop-loss per trade (%)",
        min_value=0.1, max_value=20.0,
        value=d.stop_loss_pct, step=0.1, key="sb_b_sl",
    )
    rho = st.slider(
        "Correlation with Sleeve A (ρ)",
        min_value=-1.0, max_value=1.0,
        value=d.correlation_with_a, step=0.05, key="sb_b_rho",
    )

    return SleeveBControls(
        capital_alloc_pct=float(cap_b),
        expected_return_pct=float(ret),
        expected_vol_pct=float(vol),
        expected_max_dd_pct=float(mdd),
        win_rate_pct=float(wr),
        avg_leverage=float(lev),
        funding_cost_pct=float(fund),
        stop_loss_pct=float(sl),
        correlation=float(rho),
    )


# ---------------------------------------------------------------------------
def render_status_badge(status: str) -> str:
    """Return a coloured emoji badge for a test status."""
    return {
        "pass": "🟢 Pass",
        "marginal": "🟡 Marginal",
        "fail": "🔴 Fail",
        "error": "⚪ Error",
    }.get(status, "⚪ Unknown")
