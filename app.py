"""Shannon's Demon Dashboard — Streamlit entry point.

Wires the Analysis tab and Documentation tab together. Most of the heavy
lifting lives in `analysis/` and `components/`. This file is mostly layout.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

import config as cfg
from analysis import (
    BacktestResult,
    PortfolioResult,
    SuitabilityVerdict,
    combined_stationarity_verdict,
    interpret_adf,
    interpret_half_life,
    interpret_hurst,
    interpret_kpss,
    interpret_regime,
    interpret_volatility,
    overall_suitability,
    run_adf,
    run_demon_backtest,
    run_dual_sleeve_simulation,
    run_half_life,
    run_hurst,
    run_kpss,
    run_regime_detection,
    run_volatility,
    shannon_harvest,
)
from components import charts, docs, upload, controls

# ---------------------------------------------------------------------------
logging.basicConfig(level=cfg.LOG_LEVEL, format=cfg.LOG_FORMAT)
logger = logging.getLogger("shannon-demon")


st.set_page_config(
    page_title="Shannon's Demon Dashboard",
    page_icon="👹",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Cached compute
# ---------------------------------------------------------------------------
def _hash_series(s: pd.Series) -> str:
    """Fast stable hash for caching keyed on a price series."""
    arr = s.to_numpy()
    return f"{len(arr)}_{float(arr[0]):.6f}_{float(arr[-1]):.6f}_{float(arr.mean()):.6f}"


@st.cache_data(show_spinner=False)
def _compute_stat_tests(
    series_hash: str,
    close_values: tuple[float, ...],
    close_index: tuple,
    interval_seconds: float,
    annualisation: str,
):
    """Run the full statistical suite. Cached on series-hash + settings."""
    close = pd.Series(close_values, index=pd.Index(close_index))
    interval = pd.Timedelta(seconds=interval_seconds)
    return {
        "adf": run_adf(close),
        "kpss": run_kpss(close),
        "hurst": run_hurst(close),
        "half_life": run_half_life(close, interval),
        "regime": run_regime_detection(close),
        "vol": run_volatility(close, interval, annualisation=annualisation),
    }


@st.cache_data(show_spinner=False)
def _cached_demon_backtest(
    series_hash: str,
    close_values: tuple[float, ...],
    close_index: tuple,
    weight: float,
    rebalance_rule: str,
    time_period: int,
    threshold_pct: float,
    band_sigma: float,
    band_window: int,
    cash_yield_pct: float,
    transaction_cost_bps: float,
    interval_seconds: float,
    annualisation: str,
) -> BacktestResult:
    close = pd.Series(close_values, index=pd.Index(close_index))
    return run_demon_backtest(
        close,
        weight=weight,
        rebalance_rule=rebalance_rule,
        time_period=time_period,
        threshold_pct=threshold_pct,
        band_sigma=band_sigma,
        band_window=band_window,
        cash_yield_annual_pct=cash_yield_pct,
        transaction_cost_bps=transaction_cost_bps,
        interval_seconds=interval_seconds,
        annualisation=annualisation,
    )


@st.cache_data(show_spinner=False)
def _cached_dual_sleeve(
    backtest_id: str,                        # cache key
    sleeve_a_eq_values: tuple[float, ...],
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
    # Reconstruct a minimal BacktestResult-like object for the simulator
    eq = pd.Series(sleeve_a_eq_values)
    fake_bt = BacktestResult(
        equity_curve=eq, risky_value=eq, cash_value=eq,
        rebalance_events=[], n_rebalances=0, total_costs=0.0,
        cagr=0.0, annualised_vol=0.0, max_drawdown=0.0,
        sharpe=0.0, sortino=0.0, final_value=float(eq.iloc[-1]),
    )
    return run_dual_sleeve_simulation(
        sleeve_a_backtest=fake_bt,
        sleeve_a_alloc_pct=sleeve_a_alloc_pct,
        sleeve_b_alloc_pct=sleeve_b_alloc_pct,
        sleeve_b_expected_return_pct=sleeve_b_expected_return_pct,
        sleeve_b_expected_vol_pct=sleeve_b_expected_vol_pct,
        sleeve_b_expected_max_dd_pct=sleeve_b_expected_max_dd_pct,
        sleeve_b_win_rate_pct=sleeve_b_win_rate_pct,
        sleeve_b_avg_leverage=sleeve_b_avg_leverage,
        sleeve_b_funding_cost_pct=sleeve_b_funding_cost_pct,
        sleeve_b_stop_loss_pct=sleeve_b_stop_loss_pct,
        correlation=correlation,
        n_simulations=n_simulations,
        random_seed=random_seed,
        horizon_periods=horizon_periods,
        periods_per_year=periods_per_year,
        student_t_df=student_t_df,
        risk_free_rate_pct=risk_free_rate_pct,
        mar_pct=mar_pct,
        confidence_low_pct=confidence_low_pct,
        confidence_high_pct=confidence_high_pct,
    )


# ---------------------------------------------------------------------------
def _badge_html(status: str) -> str:
    color = {"pass": "#27ae60", "marginal": "#f39c12", "fail": "#c0392b", "error": "#7f8c8d"}.get(status, "#7f8c8d")
    label = {"pass": "PASS", "marginal": "MARGINAL", "fail": "FAIL", "error": "ERROR"}.get(status, "?")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;font-weight:600;">{label}</span>'


def _verdict_box(v: SuitabilityVerdict) -> None:
    color = {"green": "#27ae60", "amber": "#f39c12", "red": "#c0392b"}[v.color]
    bg = {"green": "rgba(46,204,113,0.10)", "amber": "rgba(243,156,18,0.10)", "red": "rgba(192,57,43,0.10)"}[v.color]
    st.markdown(
        f"""
<div style="border:2px solid {color};background:{bg};padding:16px;border-radius:8px;">
  <h3 style="margin-top:0;color:{color};">Score: {v.score}/100 — {v.verdict.upper()}</h3>
  <p style="font-size:1.05em;">{v.headline}</p>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
def _section_price_overview(close: pd.Series) -> None:
    st.header("1. Price Overview")
    st.plotly_chart(charts.price_overview(close), use_container_width=True)

    with st.expander("Summary statistics"):
        desc = close.describe()
        cols = st.columns(4)
        cols[0].metric("Mean", f"{desc['mean']:.6f}")
        cols[1].metric("Std", f"{desc['std']:.6f}")
        cols[2].metric("Min", f"{desc['min']:.6f}")
        cols[3].metric("Max", f"{desc['max']:.6f}")
        cols2 = st.columns(4)
        cols2[0].metric("First", f"{close.iloc[0]:.6f}")
        cols2[1].metric("Last", f"{close.iloc[-1]:.6f}")
        cols2[2].metric("% range", f"{(desc['max']/desc['min'] - 1)*100:.2f}%")
        cols2[3].metric("Rows", f"{len(close):,}")


def _section_stationarity(results: dict) -> None:
    st.header("2. Stationarity & Mean Reversion")
    adf, kpss_r, hurst, hl = results["adf"], results["kpss"], results["hurst"], results["half_life"]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"##### ADF Test {_badge_html(adf.status)}", unsafe_allow_html=True)
        if adf.status != "error":
            st.metric("Statistic (c)", f"{adf.statistic_c:.4f}")
            st.metric("p-value (c)", f"{adf.pvalue_c:.4f}")
            st.metric("Used lag", f"{adf.used_lag_c}")
            with st.expander("Detail (constant + trend spec)"):
                st.write(f"Statistic: {adf.statistic_ct:.4f}")
                st.write(f"p-value: {adf.pvalue_ct:.4f}")
                st.write(f"Critical values (c): {adf.critical_values_c}")
                st.write(f"Critical values (ct): {adf.critical_values_ct}")
        st.info(interpret_adf(adf))

    with c2:
        st.markdown(f"##### KPSS Test {_badge_html(kpss_r.status)}", unsafe_allow_html=True)
        if kpss_r.status != "error":
            st.metric("Statistic", f"{kpss_r.statistic:.4f}")
            st.metric("p-value", f"{kpss_r.pvalue:.4f}")
            st.metric("Lag", f"{kpss_r.used_lag}")
            with st.expander("Critical values"):
                st.write(kpss_r.critical_values)
        st.info(interpret_kpss(kpss_r))

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f"##### Hurst Exponent {_badge_html(hurst.status)}", unsafe_allow_html=True)
        if hurst.status != "error":
            st.metric("Best estimate", f"{hurst.best_estimate:.3f}")
            cc = st.columns(2)
            cc[0].metric("R/S", f"{hurst.rs_hurst:.3f}")
            cc[1].metric("Variance", f"{hurst.var_hurst:.3f}")
            st.plotly_chart(charts.hurst_gauge(hurst), use_container_width=True)
        st.info(interpret_hurst(hurst))

    with c4:
        st.markdown(f"##### Half-Life of Mean Reversion {_badge_html(hl.status)}", unsafe_allow_html=True)
        if hl.status != "error":
            st.metric("β (AR1)", f"{hl.beta:.5f}")
            st.metric("β p-value", f"{hl.beta_pvalue:.4f}")
            if np.isfinite(hl.half_life_periods):
                st.metric("Half-life (periods)", f"{hl.half_life_periods:.1f}")
                st.metric("Half-life (human)", hl.half_life_human)
        st.info(interpret_half_life(hl))

    # Combined banner
    banner_text, banner_color = combined_stationarity_verdict(adf, kpss_r)
    color_map = {"green": "success", "amber": "warning", "red": "error"}
    getattr(st, color_map[banner_color])(f"**Combined ADF + KPSS verdict:** {banner_text}")


def _section_regime_vol(close: pd.Series, results: dict) -> None:
    st.header("3. Regime Stability & Volatility")
    regime, vol = results["regime"], results["vol"]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"##### Regime Stability {_badge_html(regime.status)}", unsafe_allow_html=True)
        if regime.status != "error":
            st.metric("Regime shifts detected", f"{regime.n_shifts}")
            st.caption(f"Method: {regime.method}")
            st.plotly_chart(charts.regime_chart(close, regime), use_container_width=True)
        st.info(interpret_regime(regime))

    with c2:
        st.markdown(f"##### Annualised Volatility {_badge_html(vol.status)}", unsafe_allow_html=True)
        if vol.status != "error":
            st.metric("Full-sample (ann.)", f"{vol.full_sample_annualised*100:.2f}%")
            st.metric("Last 30 periods", f"{vol.realised_30p_annualised*100:.2f}%")
            st.caption(f"Periods/year used: {vol.periods_per_year:.0f}")
            st.plotly_chart(charts.volatility_chart(vol), use_container_width=True)
        st.info(interpret_volatility(vol))


def _section_harvest(vol_result, default_w: float) -> None:
    st.header("4. Shannon Harvest Estimator")
    st.latex(r"\text{Bonus} \approx \tfrac{1}{2} \cdot w \cdot (1-w) \cdot \sigma^2")
    sigma = vol_result.full_sample_annualised if np.isfinite(vol_result.full_sample_annualised) else 0.0
    w = st.slider("Weight in risky asset (w)", 0.05, 0.95, default_w, 0.05, key="harvest_w")
    h = shannon_harvest(w, sigma)
    cols = st.columns(3)
    cols[0].metric("Annualised σ", f"{sigma*100:.2f}%")
    cols[1].metric("σ²", f"{h.annual_variance:.4f}")
    cols[2].metric("Bonus at w", f"{h.bonus_pct:.3f}%/yr")
    st.plotly_chart(charts.harvest_curve(h), use_container_width=True)
    st.caption(
        "Continuous-time approximation under GBM. Realised harvest depends on return autocorrelation, "
        "transaction costs, rebalance frequency, and survivorship."
    )


def _metrics_row(label: str, m) -> dict:
    return {
        "Sleeve": label,
        "CAGR": f"{m.cagr*100:.2f}%",
        "Vol (ann.)": f"{m.annualised_vol*100:.2f}%",
        "Sharpe": f"{m.sharpe:.2f}",
        "Sortino": f"{m.sortino:.2f}",
        "Calmar": f"{m.calmar:.2f}",
        "Max DD (mean)": f"{m.max_drawdown*100:.2f}%",
        "Worst DD (p5)": f"{m.worst_case_dd_p5*100:.2f}%",
        "Best terminal (p95)": f"{m.best_case_terminal_p95:.2f}×",
        "P(loss)": f"{m.prob_loss*100:.1f}%",
        "P(DD>50%)": f"{m.prob_dd_over_50pct*100:.1f}%",
    }


def _section_dual_sleeve(close: pd.Series, results: dict, sb: controls.SidebarSettings,
                         interval_seconds: float) -> tuple[BacktestResult, PortfolioResult, controls.SleeveAControls, controls.SleeveBControls]:
    st.header("5. Dual-Sleeve Portfolio Backtest")

    hl = results["half_life"]
    if np.isfinite(hl.half_life_periods) and hl.half_life_periods > 0:
        default_period = max(1, int(round(0.75 * hl.half_life_periods)))
    else:
        default_period = cfg.SLEEVE_A_DEFAULTS.time_rebalance_periods

    left, right = st.columns([1, 1])
    with left:
        a_ctrl = controls.render_sleeve_a(default_period)
        st.divider()
        b_ctrl = controls.render_sleeve_b(a_ctrl.capital_alloc_pct)

    series_hash = _hash_series(close)
    bt = _cached_demon_backtest(
        series_hash=series_hash,
        close_values=tuple(close.to_numpy().tolist()),
        close_index=tuple(close.index),
        weight=a_ctrl.weight,
        rebalance_rule=a_ctrl.rebalance_rule,
        time_period=a_ctrl.time_period,
        threshold_pct=a_ctrl.threshold_pct,
        band_sigma=a_ctrl.band_sigma,
        band_window=a_ctrl.band_window,
        cash_yield_pct=a_ctrl.cash_yield_pct,
        transaction_cost_bps=a_ctrl.transaction_cost_bps,
        interval_seconds=interval_seconds,
        annualisation=sb.annualisation,
    )

    # Periods/year for the MC engine
    if sb.annualisation == "calendar":
        ppy = (365.25 * 24 * 3600) / max(interval_seconds, 1.0)
    else:
        ppy = (cfg.DEFAULT_TRADING_HOURS_PER_YEAR * 3600) / max(interval_seconds, 1.0)

    # Horizon = same length as the backtest history
    horizon = max(50, len(close))

    eq_tuple = tuple(bt.equity_curve.to_numpy().tolist())

    with st.spinner(f"Running {sb.n_simulations:,} Monte Carlo simulations..."):
        portfolio = _cached_dual_sleeve(
            backtest_id=f"{series_hash}_{a_ctrl}_{b_ctrl}_{ppy}_{horizon}",
            sleeve_a_eq_values=eq_tuple,
            sleeve_a_alloc_pct=a_ctrl.capital_alloc_pct,
            sleeve_b_alloc_pct=b_ctrl.capital_alloc_pct,
            sleeve_b_expected_return_pct=b_ctrl.expected_return_pct,
            sleeve_b_expected_vol_pct=b_ctrl.expected_vol_pct,
            sleeve_b_expected_max_dd_pct=b_ctrl.expected_max_dd_pct,
            sleeve_b_win_rate_pct=b_ctrl.win_rate_pct,
            sleeve_b_avg_leverage=b_ctrl.avg_leverage,
            sleeve_b_funding_cost_pct=b_ctrl.funding_cost_pct,
            sleeve_b_stop_loss_pct=b_ctrl.stop_loss_pct,
            correlation=b_ctrl.correlation,
            n_simulations=sb.n_simulations,
            random_seed=sb.random_seed,
            horizon_periods=horizon,
            periods_per_year=ppy,
            student_t_df=cfg.SLEEVE_B_DEFAULTS.student_t_df,
            risk_free_rate_pct=sb.risk_free_rate_pct,
            mar_pct=sb.mar_pct,
            confidence_low_pct=sb.confidence_low,
            confidence_high_pct=sb.confidence_high,
        )

    with right:
        st.subheader("Sleeve A — historical equity")
        st.plotly_chart(charts.demon_equity_chart(bt, close), use_container_width=True)
        cols = st.columns(4)
        cols[0].metric("CAGR", f"{bt.cagr*100:.2f}%")
        cols[1].metric("Vol (ann.)", f"{bt.annualised_vol*100:.2f}%")
        cols[2].metric("Max DD", f"{bt.max_drawdown*100:.2f}%")
        cols[3].metric("Rebalances", f"{bt.n_rebalances}")

    st.subheader("Combined portfolio (Monte Carlo)")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.plotly_chart(charts.portfolio_equity_fan(portfolio, sb.confidence_low, sb.confidence_high),
                        use_container_width=True)
    with cc2:
        st.plotly_chart(charts.portfolio_drawdown_chart(portfolio), use_container_width=True)

    cc3, cc4 = st.columns(2)
    with cc3:
        st.plotly_chart(charts.terminal_distribution(portfolio), use_container_width=True)
    with cc4:
        st.plotly_chart(charts.sleeve_contribution_chart(portfolio), use_container_width=True)

    st.subheader("Metrics — by sleeve")
    df_m = pd.DataFrame([
        _metrics_row("A (Demon)", portfolio.metrics_a),
        _metrics_row("B (Crypto leverage)", portfolio.metrics_b),
        _metrics_row("Combined", portfolio.metrics_combined),
    ])
    st.dataframe(df_m, use_container_width=True, hide_index=True)

    return bt, portfolio, a_ctrl, b_ctrl


# ---------------------------------------------------------------------------
def _section_alloc_optimiser(close: pd.Series, sb: controls.SidebarSettings,
                             a_ctrl: controls.SleeveAControls,
                             b_ctrl: controls.SleeveBControls,
                             interval_seconds: float) -> None:
    st.header("6. Allocation Optimiser")
    st.caption(
        "Sweeps Sleeve A allocation 0–100% in 5% steps with a small Monte Carlo at each "
        "allocation. Runs on demand because each step is a fresh simulation."
    )

    if not st.button("Find optimal allocation", type="primary"):
        return

    series_hash = _hash_series(close)
    bt = _cached_demon_backtest(
        series_hash=series_hash,
        close_values=tuple(close.to_numpy().tolist()),
        close_index=tuple(close.index),
        weight=a_ctrl.weight,
        rebalance_rule=a_ctrl.rebalance_rule,
        time_period=a_ctrl.time_period,
        threshold_pct=a_ctrl.threshold_pct,
        band_sigma=a_ctrl.band_sigma,
        band_window=a_ctrl.band_window,
        cash_yield_pct=a_ctrl.cash_yield_pct,
        transaction_cost_bps=a_ctrl.transaction_cost_bps,
        interval_seconds=interval_seconds,
        annualisation=sb.annualisation,
    )
    eq_tuple = tuple(bt.equity_curve.to_numpy().tolist())

    if sb.annualisation == "calendar":
        ppy = (365.25 * 24 * 3600) / max(interval_seconds, 1.0)
    else:
        ppy = (cfg.DEFAULT_TRADING_HOURS_PER_YEAR * 3600) / max(interval_seconds, 1.0)
    horizon = max(50, len(close))

    alloc_pcts = list(np.arange(0.0, 100.0 + cfg.ALLOC_SWEEP_STEP_PCT, cfg.ALLOC_SWEEP_STEP_PCT))
    cagrs, max_dds, sortinos = [], [], []
    n_mc_sweep = max(100, sb.n_simulations // 4)
    progress = st.progress(0.0, text="Sweeping allocations...")
    for i, a in enumerate(alloc_pcts):
        result = _cached_dual_sleeve(
            backtest_id=f"sweep_{series_hash}_{a}_{a_ctrl}_{b_ctrl}",
            sleeve_a_eq_values=eq_tuple,
            sleeve_a_alloc_pct=a,
            sleeve_b_alloc_pct=100.0 - a,
            sleeve_b_expected_return_pct=b_ctrl.expected_return_pct,
            sleeve_b_expected_vol_pct=b_ctrl.expected_vol_pct,
            sleeve_b_expected_max_dd_pct=b_ctrl.expected_max_dd_pct,
            sleeve_b_win_rate_pct=b_ctrl.win_rate_pct,
            sleeve_b_avg_leverage=b_ctrl.avg_leverage,
            sleeve_b_funding_cost_pct=b_ctrl.funding_cost_pct,
            sleeve_b_stop_loss_pct=b_ctrl.stop_loss_pct,
            correlation=b_ctrl.correlation,
            n_simulations=n_mc_sweep,
            random_seed=sb.random_seed,
            horizon_periods=horizon,
            periods_per_year=ppy,
            student_t_df=cfg.SLEEVE_B_DEFAULTS.student_t_df,
            risk_free_rate_pct=sb.risk_free_rate_pct,
            mar_pct=sb.mar_pct,
            confidence_low_pct=sb.confidence_low,
            confidence_high_pct=sb.confidence_high,
        )
        cagrs.append(result.metrics_combined.cagr)
        max_dds.append(result.metrics_combined.max_drawdown)
        sortinos.append(result.metrics_combined.sortino)
        progress.progress((i + 1) / len(alloc_pcts), text=f"Sweep {i+1}/{len(alloc_pcts)}")
    progress.empty()

    optimal_idx = int(np.argmax(sortinos))
    optimal_alloc = alloc_pcts[optimal_idx]

    st.plotly_chart(
        charts.allocation_optimiser_chart(
            alloc_pcts, cagrs, max_dds, sortinos,
            current_alloc=a_ctrl.capital_alloc_pct,
            optimal_alloc=optimal_alloc,
        ),
        use_container_width=True,
    )
    st.success(
        f"Optimal Sleeve A allocation by Sortino: **{optimal_alloc:.0f}%** "
        f"(Sortino = {sortinos[optimal_idx]:.2f}, CAGR = {cagrs[optimal_idx]*100:.2f}%, "
        f"Max DD = {max_dds[optimal_idx]*100:.2f}%)"
    )


# ---------------------------------------------------------------------------
def _section_leverage(portfolio: PortfolioResult, sb: controls.SidebarSettings) -> None:
    st.header("7. Leverage Sensitivity")
    st.caption(
        "Applies leverage to the combined-portfolio per-period returns: "
        "`r_levered = L · (r_portfolio − borrow_per_period)`. Borrow cost defaults to risk-free."
    )

    lev = st.slider("Leverage applied to combined portfolio (×)",
                    cfg.LEVERAGE_MIN, cfg.LEVERAGE_MAX,
                    1.0, cfg.LEVERAGE_STEP, key="lev_main")

    levs = list(np.arange(cfg.LEVERAGE_MIN, cfg.LEVERAGE_MAX + cfg.LEVERAGE_STEP, cfg.LEVERAGE_STEP))

    paths = portfolio.combined_paths
    rets = np.diff(paths, axis=1) / paths[:, :-1]
    borrow_per_period = sb.risk_free_rate_pct / 100.0 / portfolio.periods_per_year

    def _lever(L: float):
        levered = L * (rets - borrow_per_period)
        levered_paths = np.concatenate([np.ones((paths.shape[0], 1)),
                                        np.cumprod(1.0 + levered, axis=1)], axis=1)
        cagr = (levered_paths[:, -1] / levered_paths[:, 0]) ** (
            1.0 / max(paths.shape[1] / portfolio.periods_per_year, 1e-9)
        ) - 1.0
        peaks = np.maximum.accumulate(levered_paths, axis=1)
        dd = ((levered_paths - peaks) / peaks).min(axis=1)
        excess = levered - sb.mar_pct / 100.0 / portfolio.periods_per_year
        sort = np.zeros(levered.shape[0])
        for i in range(levered.shape[0]):
            d = excess[i][excess[i] < 0]
            if len(d) > 1 and d.std(ddof=1) > 0:
                sort[i] = excess[i].mean() / d.std(ddof=1) * np.sqrt(portfolio.periods_per_year)
        return float(cagr.mean()), float(dd.mean()), float(sort.mean())

    sweep_cagr, sweep_dd, sweep_sort = [], [], []
    for L in levs:
        c, d, s = _lever(L)
        sweep_cagr.append(c)
        sweep_dd.append(d)
        sweep_sort.append(s)

    st.plotly_chart(
        charts.leverage_sensitivity_chart(levs, sweep_cagr, sweep_dd, sweep_sort),
        use_container_width=True,
    )

    cur_cagr, cur_dd, cur_sort = _lever(lev)
    cols = st.columns(3)
    cols[0].metric(f"CAGR @ {lev}×", f"{cur_cagr*100:.2f}%")
    cols[1].metric(f"Max DD @ {lev}×", f"{cur_dd*100:.2f}%")
    cols[2].metric(f"Sortino @ {lev}×", f"{cur_sort:.2f}")
    if cur_dd < -cfg.LEVERAGE_MARGIN_CALL_DD:
        st.error(f"⚠️ Drawdown at {lev}× exceeds 50% — margin-call territory.")
    elif cur_dd < -cfg.LEVERAGE_DD_RED_THRESHOLD:
        st.warning(f"⚠️ Drawdown at {lev}× exceeds 30%.")


# ---------------------------------------------------------------------------
def _section_conclusion(verdict: SuitabilityVerdict, portfolio: PortfolioResult) -> None:
    st.header("8. Conclusion")
    _verdict_box(verdict)

    cols = st.columns(2)
    with cols[0]:
        st.subheader("Top 3 reasons")
        for r in verdict.top_reasons:
            st.markdown(f"- {r}")
        st.subheader("Suggested rebalance frequency")
        st.markdown(f"> {verdict.suggested_rebalance}")
    with cols[1]:
        st.subheader("Risk envelope")
        st.markdown(f"- Max recommended leverage: **{verdict.max_recommended_leverage}×**")
        st.markdown(
            f"- Combined Sortino achieved: **{portfolio.metrics_combined.sortino:.2f}** "
            "(rule of thumb: ≥ 2.0 to support meaningful leverage)"
        )
        st.subheader("Red flags")
        if not verdict.red_flags:
            st.markdown("None detected.")
        else:
            for f in verdict.red_flags:
                st.markdown(f"- 🚩 {f}")

    with st.expander("Component score breakdown"):
        st.write(verdict.component_scores)


# ---------------------------------------------------------------------------
# Tab assembly
# ---------------------------------------------------------------------------
def render_analysis_tab() -> None:
    st.title("👹 Shannon's Demon — Suitability Dashboard")
    st.caption(
        "Upload an OHLCV CSV, run statistical mean-reversion tests, and stress-test a "
        "dual-sleeve portfolio (Demon + Crypto leverage) under Monte Carlo."
    )

    sidebar = controls.render_sidebar()
    upload_result = upload.render_uploader()
    if upload_result is None:
        st.info("👆 Upload a CSV to begin. Required column: `close`.")
        return

    df = upload_result.df
    close = df["close"]

    _section_price_overview(close)

    series_hash = _hash_series(close)
    with st.spinner("Running statistical tests..."):
        results = _compute_stat_tests(
            series_hash=series_hash,
            close_values=tuple(close.to_numpy().tolist()),
            close_index=tuple(close.index),
            interval_seconds=upload_result.interval_seconds,
            annualisation=sidebar.annualisation,
        )

    _section_stationarity(results)
    _section_regime_vol(close, results)
    _section_harvest(results["vol"], cfg.SLEEVE_A_DEFAULTS.demon_weight)

    bt, portfolio, a_ctrl, b_ctrl = _section_dual_sleeve(
        close, results, sidebar, upload_result.interval_seconds,
    )

    _section_alloc_optimiser(close, sidebar, a_ctrl, b_ctrl, upload_result.interval_seconds)
    _section_leverage(portfolio, sidebar)

    verdict = overall_suitability(
        results["adf"], results["kpss"], results["hurst"],
        results["half_life"], results["regime"], results["vol"],
    )
    _section_conclusion(verdict, portfolio)


def main() -> None:
    """Top-level Streamlit entry point."""
    tab_analysis, tab_docs, tab_assumptions = st.tabs(
        ["📊 Analysis", "📘 Documentation", "⚠️ Assumptions & Limitations"]
    )
    with tab_analysis:
        render_analysis_tab()
    with tab_docs:
        docs.render_documentation_tab()
    with tab_assumptions:
        docs.render_assumptions_tab()


if __name__ == "__main__":
    main()
