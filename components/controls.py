"""Reusable Streamlit control widgets.

The sidebar is now a sticky table of contents. Power-user / Monte Carlo
parameters live in a top-of-page expander on the Analysis tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import streamlit as st

import config as cfg


# ---------------------------------------------------------------------------
# Section index used by both the TOC and the section renderers
# ---------------------------------------------------------------------------
SECTIONS: list[tuple[str, str]] = [
    ("section-1", "1. Price Overview"),
    ("section-2", "2. Stationarity & Mean Reversion"),
    ("section-3", "3. Regime & Volatility"),
    ("section-4", "4. Shannon Harvest"),
    ("section-5", "5. Dual-Sleeve Backtest"),
    ("section-6", "6. Allocation Optimiser"),
    ("section-7", "7. Leverage Sensitivity"),
    ("section-8", "8. Conclusion"),
]


def render_sidebar_toc() -> None:
    """Sticky sidebar containing only the table of contents and a reset."""
    st.sidebar.markdown(
        '<div class="toc-title">CONTENTS</div>',
        unsafe_allow_html=True,
    )
    for anchor, label in SECTIONS:
        st.sidebar.markdown(
            f'<a class="toc-link" href="#{anchor}">{label}</a>',
            unsafe_allow_html=True,
        )

    st.sidebar.markdown('<div class="toc-spacer"></div>', unsafe_allow_html=True)

    if st.sidebar.button("Reset to defaults", use_container_width=True, key="sb_reset"):
        for k in list(st.session_state.keys()):
            if k.startswith(("sb_", "sa_", "harvest_", "lev_", "date_", "row_")):
                del st.session_state[k]
        st.rerun()


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


def render_settings_expander() -> SidebarSettings:
    """Top-of-page expander housing power-user parameters."""
    with st.expander("Settings & power-user parameters", expanded=False):
        st.caption(
            "Defaults are sensible for most analyses. Adjust only if you know what you "
            "are doing — these change Monte Carlo behaviour, annualisation, and risk-free "
            "assumptions across the entire dashboard."
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            n_sims = st.slider(
                "Monte Carlo iterations",
                min_value=cfg.MC_DEFAULTS.n_simulations_min,
                max_value=cfg.MC_DEFAULTS.n_simulations_max,
                value=cfg.MC_DEFAULTS.n_simulations,
                step=100, key="sb_mc_n",
                help="More iterations = smoother bands, slower compute.",
            )
            seed = st.number_input(
                "Random seed", min_value=0, max_value=10**9,
                value=cfg.MC_DEFAULTS.random_seed, step=1, key="sb_mc_seed",
            )
        with c2:
            annual_choice = st.radio(
                "Annualisation basis",
                options=["trading", "calendar"], index=0,
                format_func=lambda x: "Trading hours (252 d/yr)" if x == "trading"
                                      else "Calendar (24/7)",
                key="sb_mc_annual",
                help="Use 'calendar' for 24/7 markets like crypto.",
            )
            days_per_year = st.number_input(
                "Trading days per year",
                min_value=200, max_value=370,
                value=cfg.DEFAULT_TRADING_DAYS_PER_YEAR if annual_choice == "trading"
                      else cfg.CRYPTO_DAYS_PER_YEAR,
                step=1, key="sb_mc_dpy",
            )
        with c3:
            rf = st.number_input(
                "Risk-free rate (%/yr)",
                min_value=0.0, max_value=20.0,
                value=cfg.MC_DEFAULTS.risk_free_rate_pct, step=0.25, key="sb_mc_rf",
            )
            mar = st.number_input(
                "MAR for Sortino (%/yr)",
                min_value=-20.0, max_value=50.0,
                value=cfg.MC_DEFAULTS.mar_pct, step=0.25, key="sb_mc_mar",
            )

        bands = st.radio(
            "Monte Carlo confidence bands",
            options=["10/90", "5/95"], index=0, key="sb_mc_bands",
            horizontal=True,
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


# Backwards-compat alias (older code may still call render_sidebar)
def render_sidebar() -> SidebarSettings:
    return render_settings_expander()


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
    st.markdown(
        '<div class="sleeve-title">Sleeve A — Shannon\'s Demon</div>',
        unsafe_allow_html=True,
    )
    st.caption("Mean-reversion rebalancing on the uploaded asset, paired with cash.")

    cap = st.slider("Capital allocation to Sleeve A (%)",
                    0.0, 100.0, d.capital_alloc_pct, 1.0, key="sa_cap")
    w = st.slider("Demon weight w (risky / cash)",
                  0.10, 0.90, d.demon_weight, 0.05, key="sa_w")
    rule = st.radio(
        "Rebalance rule", options=["time", "threshold", "band"], index=0,
        format_func={"time": "Time-based", "threshold": "Weight-drift threshold",
                     "band": "Band (sigma from rolling mean)"}.get,
        key="sa_rule",
    )

    if rule == "time":
        period = st.number_input(
            "Rebalance every N periods",
            1, 10_000, int(default_time_period), 1, key="sa_period",
            help=f"Default = 0.75 x half-life ({default_time_period} periods).",
        )
        threshold = d.threshold_drift_pct
        band_s = d.band_sigma
    elif rule == "threshold":
        threshold = st.slider(
            "Drift threshold (%)",
            1.0, 50.0, d.threshold_drift_pct, 0.5, key="sa_threshold",
        )
        period = default_time_period
        band_s = d.band_sigma
    else:
        band_s = st.slider(
            "Band size (sigma from rolling mean)",
            0.25, 4.0, d.band_sigma, 0.25, key="sa_band",
        )
        period = default_time_period
        threshold = d.threshold_drift_pct

    band_window = st.number_input(
        "Rolling window for band rule (periods)",
        20, 2000, 90, 10, key="sa_band_window",
    )
    cash_y = st.number_input(
        "Cash yield (%/yr)", 0.0, 15.0, d.cash_yield_pct, 0.25, key="sa_cashy",
    )
    tcost = st.number_input(
        "Transaction cost (bps per rebalance)",
        0.0, 200.0, d.transaction_cost_bps, 1.0, key="sa_tcost",
    )

    return SleeveAControls(
        capital_alloc_pct=float(cap), weight=float(w),
        rebalance_rule=rule, time_period=int(period),
        threshold_pct=float(threshold),
        band_sigma=float(band_s), band_window=int(band_window),
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
    d = cfg.SLEEVE_B_DEFAULTS
    st.markdown(
        '<div class="sleeve-title">Sleeve B — Crypto Leverage</div>',
        unsafe_allow_html=True,
    )
    st.caption("Parametric Monte Carlo of a leveraged directional book — your inputs are the strategy's expected behaviour.")

    cap_b = max(0.0, 100.0 - sleeve_a_alloc)
    st.metric("Capital allocation to Sleeve B (%)", f"{cap_b:.1f}%",
              help="Auto-complement of Sleeve A. Adjust the Sleeve A slider to change.")

    ret = st.number_input("Expected annual return (%)", -50.0, 500.0,
                          d.expected_annual_return_pct, 1.0, key="sb_b_ret")
    vol = st.number_input("Expected annual volatility (%)", 1.0, 500.0,
                          d.expected_annual_vol_pct, 1.0, key="sb_b_vol")
    mdd = st.number_input("Expected max drawdown (%)", 1.0, 99.0,
                          d.expected_max_drawdown_pct, 1.0, key="sb_b_mdd")
    wr = st.number_input("Win rate (%)", 10.0, 90.0,
                         d.win_rate_pct, 1.0, key="sb_b_wr")
    lev = st.number_input("Average leverage used", 1.0, 20.0,
                          d.avg_leverage, 0.5, key="sb_b_lev")
    fund = st.number_input("Funding / borrow cost (%/yr)", 0.0, 50.0,
                           d.funding_cost_pct, 0.5, key="sb_b_fund")
    sl = st.number_input("Stop-loss per trade (%)", 0.1, 20.0,
                         d.stop_loss_pct, 0.1, key="sb_b_sl")
    rho = st.slider("Correlation with Sleeve A (rho)", -1.0, 1.0,
                    d.correlation_with_a, 0.05, key="sb_b_rho")

    return SleeveBControls(
        capital_alloc_pct=float(cap_b),
        expected_return_pct=float(ret),
        expected_vol_pct=float(vol),
        expected_max_dd_pct=float(mdd),
        win_rate_pct=float(wr), avg_leverage=float(lev),
        funding_cost_pct=float(fund),
        stop_loss_pct=float(sl), correlation=float(rho),
    )


# ---------------------------------------------------------------------------
def render_status_badge(status: str) -> str:
    """Plain-text status label, no emoji."""
    return {
        "pass": "Pass",
        "marginal": "Marginal",
        "fail": "Fail",
        "error": "Error",
    }.get(status, "Unknown")
