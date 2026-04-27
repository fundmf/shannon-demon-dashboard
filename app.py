"""Shannon's Demon Dashboard — Streamlit entry point.

Wires the Analysis, Documentation, and Assumptions tabs together. Most of
the heavy lifting lives in `analysis/` and `components/`. This file is
mostly layout, theming, and section assembly.
"""

from __future__ import annotations

import logging
from datetime import date as _date
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
from components import charts, controls, docs, upload

# ---------------------------------------------------------------------------
logging.basicConfig(level=cfg.LOG_LEVEL, format=cfg.LOG_FORMAT)
logger = logging.getLogger("shannon-demon")


st.set_page_config(
    page_title="Shannon's Demon Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Custom CSS — quant institutional dark aesthetic
# ---------------------------------------------------------------------------
_CUSTOM_CSS = f"""
<style>
:root {{
  --bg: {cfg.THEME_BG};
  --card: {cfg.THEME_CARD};
  --card-alt: {cfg.THEME_CARD_ALT};
  --border: {cfg.THEME_BORDER};
  --text: {cfg.THEME_TEXT};
  --muted: {cfg.THEME_TEXT_MUTED};
  --accent: {cfg.THEME_ACCENT};
  --success: {cfg.THEME_SUCCESS};
  --warning: {cfg.THEME_WARNING};
  --danger: {cfg.THEME_DANGER};
  --info: {cfg.THEME_INFO};
}}

html, body, [class*="css"], .stApp {{
  font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-feature-settings: 'tnum' 1, 'cv02' 1;
}}

/* main container width */
.main .block-container {{
  padding-top: 1.5rem;
  padding-bottom: 4rem;
  max-width: 1400px;
}}

/* H1 / titles */
h1, .stApp h1 {{
  color: var(--text) !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.5rem;
  margin-bottom: 0.25rem !important;
}}
h2 {{ color: var(--text) !important; font-weight: 600 !important; }}
h3, h4, h5 {{ color: var(--text) !important; }}

/* tab headers — flatter, accent underline on active */
.stTabs [data-baseweb="tab-list"] {{
  gap: 4px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0;
}}
.stTabs [data-baseweb="tab"] {{
  background-color: transparent !important;
  color: var(--muted) !important;
  border-radius: 0 !important;
  padding: 8px 18px !important;
  font-weight: 500 !important;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  font-size: 0.85em !important;
}}
.stTabs [aria-selected="true"] {{
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
  background-color: transparent !important;
}}

/* Section card — wraps each numbered block */
.section-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 24px 28px;
  margin: 0 0 28px 0;
}}
.section-anchor {{
  display: block;
  position: relative;
  top: -70px;
  visibility: hidden;
}}
.section-num {{
  color: var(--accent);
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 0.85em;
  letter-spacing: 0.15em;
  font-weight: 600;
  text-transform: uppercase;
}}
.section-title {{
  font-size: 1.45em;
  font-weight: 600;
  color: var(--text);
  margin-top: 0.15em;
  margin-bottom: 0.25em;
  letter-spacing: -0.01em;
}}
.section-desc {{
  color: var(--muted);
  font-size: 0.94em;
  margin-bottom: 20px;
  line-height: 1.5;
  border-bottom: 1px solid var(--border);
  padding-bottom: 14px;
}}

/* sub-headings inside a section */
.subhead {{
  font-size: 1.05em;
  font-weight: 600;
  color: var(--text);
  margin: 14px 0 6px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}}
.subhead-desc {{
  color: var(--muted);
  font-size: 0.85em;
  margin-bottom: 10px;
}}

/* sleeve panel titles */
.sleeve-title {{
  color: var(--accent);
  font-weight: 600;
  font-size: 1.05em;
  letter-spacing: 0.02em;
  margin-bottom: 4px;
  border-left: 3px solid var(--accent);
  padding-left: 10px;
}}

/* status pills */
.pill {{
  display: inline-block;
  padding: 2px 10px;
  border-radius: 3px;
  font-size: 0.72em;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}}
.pill-pass {{ background: rgba(63,185,80,0.15); color: var(--success); border: 1px solid rgba(63,185,80,0.4); }}
.pill-marginal {{ background: rgba(210,153,34,0.15); color: var(--warning); border: 1px solid rgba(210,153,34,0.4); }}
.pill-fail {{ background: rgba(218,54,51,0.15); color: var(--danger); border: 1px solid rgba(218,54,51,0.4); }}
.pill-error {{ background: rgba(139,148,158,0.15); color: var(--muted); border: 1px solid var(--border); }}

/* metric tweaks */
[data-testid="stMetric"] {{
  background: var(--card-alt);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 14px;
}}
[data-testid="stMetricLabel"] {{
  color: var(--muted) !important;
  font-size: 0.78em !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 500;
}}
[data-testid="stMetricValue"] {{
  color: var(--text) !important;
  font-family: 'JetBrains Mono', 'Consolas', monospace !important;
  font-weight: 600 !important;
  font-size: 1.4em !important;
}}

/* dataframes */
[data-testid="stDataFrame"] {{
  border: 1px solid var(--border);
  border-radius: 4px;
}}

/* sidebar TOC */
[data-testid="stSidebar"] {{
  background-color: var(--card) !important;
  border-right: 1px solid var(--border);
}}
[data-testid="stSidebar"] > div:first-child {{
  padding-top: 1rem;
}}
.toc-title {{
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 0.78em;
  letter-spacing: 0.18em;
  color: var(--accent);
  font-weight: 600;
  padding: 4px 14px 14px 14px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}}
.toc-link {{
  display: block;
  padding: 7px 14px;
  color: var(--muted);
  text-decoration: none !important;
  font-size: 0.92em;
  border-left: 2px solid transparent;
  transition: all 0.12s ease;
}}
.toc-link:hover {{
  color: var(--accent);
  background: var(--card-alt);
  border-left-color: var(--accent);
}}
.toc-spacer {{ height: 18px; }}

/* expanders */
.streamlit-expanderHeader {{
  background-color: var(--card-alt) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 4px !important;
}}

/* buttons — primary uses accent */
.stButton > button {{
  border: 1px solid var(--border);
  background: var(--card-alt);
  color: var(--text);
  font-weight: 500;
  border-radius: 4px;
  transition: all 0.12s ease;
}}
.stButton > button:hover {{
  border-color: var(--accent);
  color: var(--accent);
}}
.stButton > button[kind="primary"] {{
  background: var(--accent);
  color: var(--bg);
  border: 1px solid var(--accent);
}}
.stButton > button[kind="primary"]:hover {{
  background: var(--text);
  color: var(--bg);
  border-color: var(--text);
}}

/* alert boxes */
.stAlert {{ border-radius: 4px; }}

/* verdict box */
.verdict-box {{
  border-radius: 6px;
  padding: 18px 22px;
  margin-bottom: 18px;
}}
.verdict-box h3 {{
  margin-top: 0;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 1.15em;
  letter-spacing: 0.06em;
}}

/* interpretation box (after metrics table) */
.interp-box {{
  background: var(--card-alt);
  border-left: 3px solid var(--info);
  padding: 14px 18px;
  margin: 12px 0 0 0;
  border-radius: 0 4px 4px 0;
  color: var(--text);
  font-size: 0.95em;
  line-height: 1.55;
}}
.interp-box strong {{ color: var(--accent); }}

/* hide Streamlit hamburger and "Made with Streamlit" footer */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}

/* scrollbar */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--muted); }}

/* ===========================================================
   Keyword highlighting system
   Hover any highlighted word for the category meaning.
   =========================================================== */
.kw-test     {{ color: #D4A858; font-weight: 600; }}
.kw-num      {{ color: #5DD3D8; font-family: 'JetBrains Mono','Consolas',monospace; font-weight: 500; }}
.kw-good     {{ color: #56D364; font-weight: 600; }}
.kw-warn     {{ color: #E0A45C; font-weight: 600; }}
.kw-bad      {{ color: #FF6B6B; font-weight: 600; }}
.kw-concept  {{ color: #79B8FF; font-weight: 600; }}
.kw-caveat   {{ color: #B392F0; font-weight: 600; }}

/* legend — top of every tab */
.kw-legend {{
  display: flex;
  flex-wrap: wrap;
  gap: 14px 22px;
  padding: 10px 16px;
  background: var(--card-alt);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 4px;
  font-size: 0.82em;
  margin: 4px 0 22px 0;
  color: var(--muted);
  align-items: center;
}}
.kw-legend-label {{
  font-family: 'JetBrains Mono','Consolas',monospace;
  font-size: 0.78em;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
  margin-right: 4px;
}}
.kw-legend span span {{ font-weight: 600; }}

/* Documentation section card header tag */
.doc-section-tag {{
  color: var(--accent);
  font-family: 'JetBrains Mono','Consolas',monospace;
  font-size: 0.78em;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 4px 0 12px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.doc-section-tag .doc-section-tag-right {{
  color: var(--muted);
  font-weight: 500;
  letter-spacing: 0.10em;
}}

/* Documentation search bar */
.doc-search-info {{
  color: var(--muted);
  font-size: 0.85em;
  margin: 4px 0 14px 0;
  font-family: 'JetBrains Mono','Consolas',monospace;
  letter-spacing: 0.04em;
}}
.doc-search-info strong {{
  color: var(--accent);
}}

/* Search match highlight */
mark.search-hit {{
  background: rgba(232, 192, 96, 0.32);
  color: #FFEFC2;
  padding: 1px 3px;
  border-radius: 2px;
  font-weight: 600;
  box-shadow: inset 0 -1px 0 rgba(232,192,96,0.6);
}}
</style>
"""


# ---------------------------------------------------------------------------
# Cached compute
# ---------------------------------------------------------------------------
def _hash_series(s: pd.Series) -> str:
    arr = s.to_numpy()
    if len(arr) == 0:
        return "empty"
    return f"{len(arr)}_{float(arr[0]):.6f}_{float(arr[-1]):.6f}_{float(arr.mean()):.6f}"


@st.cache_data(show_spinner=False)
def _compute_stat_tests(series_hash, close_values, close_index, interval_seconds, annualisation):
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
    series_hash, close_values, close_index,
    weight, rebalance_rule, time_period, threshold_pct, band_sigma, band_window,
    cash_yield_pct, transaction_cost_bps, interval_seconds, annualisation,
) -> BacktestResult:
    close = pd.Series(close_values, index=pd.Index(close_index))
    return run_demon_backtest(
        close, weight=weight, rebalance_rule=rebalance_rule,
        time_period=time_period, threshold_pct=threshold_pct,
        band_sigma=band_sigma, band_window=band_window,
        cash_yield_annual_pct=cash_yield_pct,
        transaction_cost_bps=transaction_cost_bps,
        interval_seconds=interval_seconds, annualisation=annualisation,
    )


@st.cache_data(show_spinner=False)
def _cached_dual_sleeve(
    backtest_id, sleeve_a_eq_values,
    sleeve_a_alloc_pct, sleeve_b_alloc_pct,
    sleeve_b_expected_return_pct, sleeve_b_expected_vol_pct,
    sleeve_b_expected_max_dd_pct, sleeve_b_win_rate_pct,
    sleeve_b_avg_leverage, sleeve_b_funding_cost_pct,
    sleeve_b_stop_loss_pct, correlation,
    n_simulations, random_seed, horizon_periods, periods_per_year,
    student_t_df, risk_free_rate_pct, mar_pct,
    confidence_low_pct, confidence_high_pct,
) -> PortfolioResult:
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
        n_simulations=n_simulations, random_seed=random_seed,
        horizon_periods=horizon_periods, periods_per_year=periods_per_year,
        student_t_df=student_t_df,
        risk_free_rate_pct=risk_free_rate_pct, mar_pct=mar_pct,
        confidence_low_pct=confidence_low_pct,
        confidence_high_pct=confidence_high_pct,
    )


# ---------------------------------------------------------------------------
# Keyword-highlight legend (rendered once at the top of each tab)
# ---------------------------------------------------------------------------
KW_LEGEND_HTML = (
    '<div class="kw-legend">'
    '<span class="kw-legend-label">LEGEND</span>'
    '<span><span class="kw-test">tests / methods</span></span>'
    '<span><span class="kw-num">numbers / thresholds</span></span>'
    '<span><span class="kw-good">positive signal</span></span>'
    '<span><span class="kw-warn">caution</span></span>'
    '<span><span class="kw-bad">risk</span></span>'
    '<span><span class="kw-concept">core concept</span></span>'
    '<span><span class="kw-caveat">assumption / caveat</span></span>'
    '</div>'
)


# ---------------------------------------------------------------------------
# Section / status helpers
# ---------------------------------------------------------------------------
def _pill(status: str) -> str:
    cls = {"pass": "pill-pass", "marginal": "pill-marginal",
           "fail": "pill-fail", "error": "pill-error"}.get(status, "pill-error")
    label = {"pass": "PASS", "marginal": "MARGINAL",
             "fail": "FAIL", "error": "ERROR"}.get(status, "?")
    return f'<span class="pill {cls}">{label}</span>'


def _section_open(anchor: str, num: str, title: str, desc: str) -> None:
    """Render section header (title + 1-line description) inside a card."""
    st.markdown(f'<a class="section-anchor" id="{anchor}"></a>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-num">{num}</div>'
        f'<div class="section-title">{title}</div>'
        f'<div class="section-desc">{desc}</div>',
        unsafe_allow_html=True,
    )


def _subhead(label: str, status: Optional[str] = None, desc: Optional[str] = None) -> None:
    pill = _pill(status) if status else ""
    st.markdown(f'<div class="subhead">{label} {pill}</div>', unsafe_allow_html=True)
    if desc:
        st.markdown(f'<div class="subhead-desc">{desc}</div>', unsafe_allow_html=True)


def _verdict_box(v: SuitabilityVerdict) -> None:
    color = {"green": cfg.THEME_SUCCESS,
             "amber": cfg.THEME_WARNING,
             "red": cfg.THEME_DANGER}[v.color]
    bg = {"green": "rgba(63,185,80,0.10)",
          "amber": "rgba(210,153,34,0.10)",
          "red": "rgba(218,54,51,0.10)"}[v.color]
    st.markdown(
        f"""<div class="verdict-box" style="border:1px solid {color};background:{bg};">
          <h3 style="color:{color};">SCORE {v.score}/100 — {v.verdict.upper()}</h3>
          <p style="font-size:1.02em;margin:0;color:{cfg.THEME_TEXT};">{v.headline}</p>
        </div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Date range selector
# ---------------------------------------------------------------------------
def _render_date_filter(close: pd.Series, has_time_index: bool) -> Optional[pd.Series]:
    """Render a date / row range selector; return the filtered close series."""
    st.markdown(
        '<div class="section-num">FILTER</div>'
        '<div class="section-title">Analysis date range</div>'
        '<div class="section-desc">Restrict every <span class="kw-test">test</span>, '
        '<span class="kw-concept">backtest</span>, and <span class="kw-test">Monte Carlo</span> '
        'below to a date window. Defaults to the <span class="kw-good">full uploaded range</span>.</div>',
        unsafe_allow_html=True,
    )

    if has_time_index and isinstance(close.index, pd.DatetimeIndex):
        min_d: _date = close.index[0].to_pydatetime().date()
        max_d: _date = close.index[-1].to_pydatetime().date()

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            start = st.date_input("Start date", value=min_d,
                                  min_value=min_d, max_value=max_d, key="date_start")
        with c2:
            end = st.date_input("End date", value=max_d,
                                min_value=min_d, max_value=max_d, key="date_end")
        with c3:
            st.metric("Selected window",
                      f"{(pd.Timestamp(end) - pd.Timestamp(start)).days} days",
                      help="Length of the window currently selected.")

        if start > end:
            st.error("Start date must be on or before end date.")
            return None

        mask = (close.index.date >= start) & (close.index.date <= end)
        out = close[mask]
        if len(out) < cfg.MIN_OBS_HARD_BLOCK:
            st.error(f"Filtered window has only {len(out)} rows — minimum "
                     f"{cfg.MIN_OBS_HARD_BLOCK} required. Widen the range.")
            return None
        if len(out) < cfg.MIN_OBS_SOFT_WARN:
            st.warning(f"Filtered window has {len(out)} rows. Statistical tests need "
                       f">= {cfg.MIN_OBS_SOFT_WARN} for reliable estimates.")
        st.caption(f"Filtered: **{len(out):,}** observations between {start} and {end}.")
        return out
    else:
        n = len(close)
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            start_idx = st.number_input("Start row", 0, max(0, n - 2),
                                        0, 1, key="row_start")
        with c2:
            end_idx = st.number_input("End row", 1, n - 1, n - 1, 1, key="row_end")
        with c3:
            st.metric("Selected rows", f"{end_idx - start_idx + 1:,}")
        if start_idx >= end_idx:
            st.error("Start row must be before end row.")
            return None
        return close.iloc[int(start_idx): int(end_idx) + 1]


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def _section_price_overview(close: pd.Series) -> None:
    with st.container(border=True):
        _section_open(
            "section-1", "01 / SECTION",
            "Price Overview",
            'Visual snapshot of the uploaded series — close price with a '
            '<span class="kw-concept">rolling mean</span> and '
            '<span class="kw-num">+/-1 sigma</span> / <span class="kw-num">+/-2 sigma</span> bands. '
            'Use this to eyeball whether the asset behaves in a way that '
            '<span class="kw-concept">rebalancing</span> could exploit.',
        )
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
            cols2[2].metric("Range", f"{(desc['max']/desc['min'] - 1)*100:.2f}%")
            cols2[3].metric("Rows", f"{len(close):,}")


def _section_stationarity(results: dict) -> None:
    with st.container(border=True):
        _section_open(
            "section-2", "02 / SECTION",
            "Stationarity & Mean Reversion",
            'Tests whether the series tends to <span class="kw-good">return to its average</span>. '
            '<span class="kw-test">ADF</span> and <span class="kw-test">KPSS</span> check this from different angles; '
            '<span class="kw-test">Hurst</span> measures persistence; '
            '<span class="kw-test">half-life</span> estimates how fast the series snaps back.',
        )
        adf, kpss_r, hurst, hl = results["adf"], results["kpss"], results["hurst"], results["half_life"]

        c1, c2 = st.columns(2)
        with c1:
            _subhead("ADF Test", adf.status,
                     'Tests if the series is <span class="kw-good">stationary</span>. '
                     'Low <span class="kw-num">p-value</span> = <span class="kw-good">mean-reverting</span>.')
            if adf.status != "error":
                st.metric("Statistic (c)", f"{adf.statistic_c:.4f}",
                          help="Augmented Dickey-Fuller test statistic. More negative = stronger mean reversion.")
                st.metric("p-value (c)", f"{adf.pvalue_c:.4f}",
                          help="< 0.05 = reject the null of a unit root => stationary.")
                st.metric("Used lag", f"{adf.used_lag_c}",
                          help="Lag selected by AIC.")
                with st.expander("Detail (constant + trend spec)"):
                    st.write(f"Statistic: {adf.statistic_ct:.4f}")
                    st.write(f"p-value: {adf.pvalue_ct:.4f}")
                    st.write(f"Critical values (c): {adf.critical_values_c}")
                    st.write(f"Critical values (ct): {adf.critical_values_ct}")
            st.info(interpret_adf(adf))

        with c2:
            _subhead("KPSS Test", kpss_r.status,
                     'Tests the opposite null. High <span class="kw-num">p-value</span> = '
                     '<span class="kw-good">stationary around a level</span>.')
            if kpss_r.status != "error":
                st.metric("Statistic", f"{kpss_r.statistic:.4f}",
                          help="KPSS statistic. Low values support stationarity.")
                st.metric("p-value", f"{kpss_r.pvalue:.4f}",
                          help="> 0.05 = fail to reject stationarity (good for our use).")
                st.metric("Lag", f"{kpss_r.used_lag}")
                with st.expander("Critical values"):
                    st.write(kpss_r.critical_values)
            st.info(interpret_kpss(kpss_r))

        c3, c4 = st.columns(2)
        with c3:
            _subhead("Hurst Exponent", hurst.status,
                     'Memory of the series. <span class="kw-num">&lt;0.5</span> '
                     '<span class="kw-good">reverts</span>; <span class="kw-num">~0.5</span> '
                     '<span class="kw-warn">random walk</span>; <span class="kw-num">&gt;0.5</span> '
                     '<span class="kw-bad">trends</span>.')
            if hurst.status != "error":
                st.metric("Best estimate", f"{hurst.best_estimate:.3f}",
                          help="Mean of the two methods, or the more reliable one if they disagree.")
                cc = st.columns(2)
                cc[0].metric("R/S", f"{hurst.rs_hurst:.3f}",
                             help="Rescaled-range method.")
                cc[1].metric("Variance", f"{hurst.var_hurst:.3f}",
                             help="Variance-of-lagged-differences method.")
                st.plotly_chart(charts.hurst_gauge(hurst), use_container_width=True)
            st.info(interpret_hurst(hurst))

        with c4:
            _subhead("Half-Life of Mean Reversion", hl.status,
                     'How long it takes the series to <span class="kw-good">snap halfway back</span> to its '
                     '<span class="kw-concept">mean</span>.')
            if hl.status != "error":
                st.metric("Beta (AR1)", f"{hl.beta:.5f}",
                          help="AR(1) coefficient. Negative = mean-reverting; closer to -1 = faster.")
                st.metric("Beta p-value", f"{hl.beta_pvalue:.4f}",
                          help="< 0.05 = the mean reversion is statistically real.")
                if np.isfinite(hl.half_life_periods):
                    st.metric("Half-life (periods)", f"{hl.half_life_periods:.1f}")
                    st.metric("Half-life (human)", hl.half_life_human)
            st.info(interpret_half_life(hl))

        banner_text, banner_color = combined_stationarity_verdict(adf, kpss_r)
        color_map = {"green": "success", "amber": "warning", "red": "error"}
        getattr(st, color_map[banner_color])(f"**Combined ADF + KPSS verdict:** {banner_text}")


def _section_regime_vol(close: pd.Series, results: dict) -> None:
    with st.container(border=True):
        _section_open(
            "section-3", "03 / SECTION",
            "Regime Stability & Volatility",
            'Detects <span class="kw-warn">regime shifts</span> (sudden changes in level) and measures '
            'the asset\'s <span class="kw-concept">annualised volatility</span> — the '
            '<span class="kw-good">raw material the demon harvests</span>.',
        )
        regime, vol = results["regime"], results["vol"]

        c1, c2 = st.columns(2)
        with c1:
            _subhead("Regime Stability", regime.status,
                     'Counts moments where the series <span class="kw-warn">clearly shifts level</span>.')
            if regime.status != "error":
                st.metric("Regime shifts detected", f"{regime.n_shifts}",
                          help="Times the rolling mean moved > 2 sigma vs the prior window.")
                st.caption(f"Method: {regime.method}")
                st.plotly_chart(charts.regime_chart(close, regime), use_container_width=True)
            st.info(interpret_regime(regime))

        with c2:
            _subhead("Annualised Volatility", vol.status,
                     'Annualised <span class="kw-test">stdev of log returns</span>. The bigger this is, '
                     'the more <span class="kw-good">rebalancing fuel</span>.')
            if vol.status != "error":
                st.metric("Full-sample (ann.)", f"{vol.full_sample_annualised*100:.2f}%",
                          help="Annualised stdev across the whole window.")
                st.metric("Last 30 periods", f"{vol.realised_30p_annualised*100:.2f}%",
                          help="Recent realised volatility — does it match the long run?")
                st.caption(f"Periods/year used: {vol.periods_per_year:.0f}")
                st.plotly_chart(charts.volatility_chart(vol), use_container_width=True)
            st.info(interpret_volatility(vol))


def _section_harvest(vol_result, default_w: float) -> None:
    with st.container(border=True):
        _section_open(
            "section-4", "04 / SECTION",
            "Shannon Harvest Estimator",
            'Theoretical <span class="kw-good">upper bound</span> on the annualised '
            '<span class="kw-concept">rebalancing bonus</span>, given the measured '
            '<span class="kw-concept">volatility</span> and your weight in the risky asset. '
            '<span class="kw-caveat">Continuous-time GBM approximation</span>.',
        )
        st.latex(r"\text{Bonus} \approx \tfrac{1}{2} \cdot w \cdot (1-w) \cdot \sigma^2")
        sigma = vol_result.full_sample_annualised if np.isfinite(vol_result.full_sample_annualised) else 0.0
        w = st.slider("Weight in risky asset (w)", 0.05, 0.95, default_w, 0.05, key="harvest_w")
        h = shannon_harvest(w, sigma)
        cols = st.columns(3)
        cols[0].metric("Annualised sigma", f"{sigma*100:.2f}%",
                       help="Volatility input to the harvest formula.")
        cols[1].metric("sigma squared", f"{h.annual_variance:.4f}",
                       help="Variance — the fuel for rebalancing.")
        cols[2].metric("Bonus at w", f"{h.bonus_pct:.3f}%/yr",
                       help="Annualised expected harvest given your weight.")
        st.plotly_chart(charts.harvest_curve(h), use_container_width=True)
        st.caption(
            "Continuous-time approximation under GBM. Realised harvest depends on return autocorrelation, "
            "transaction costs, rebalance frequency, and survivorship."
        )


# ---------------------------------------------------------------------------
# Metrics: explanations + interpretation
# ---------------------------------------------------------------------------
_METRIC_HELP: dict[str, str] = {
    "Sleeve": "Which book the metrics row describes.",
    "CAGR": "Compound Annual Growth Rate — geometric average return per year. The single 'how much did I make?' number.",
    "Vol (ann.)": "Annualised standard deviation of returns. Higher = more daily wiggle. Bigger isn't bad if it's symmetric.",
    "Sharpe": "Excess return per unit of total volatility. >1 decent, >2 great. Penalises both upside and downside vol equally.",
    "Sortino": "Like Sharpe but only counts downside volatility. The fairer measure for skewed strategies. >2 is the threshold for safely supporting leverage.",
    "Calmar": "CAGR divided by max drawdown. A pure pain-vs-gain metric. >1 = you make more per year than the worst loss you suffered.",
    "Max DD (mean)": "Average peak-to-trough loss across all simulated paths. Your typical worst day.",
    "Worst DD (p5)": "5th-percentile drawdown — the worst loss seen in the bad 5% of simulations. Plan for this happening.",
    "Best terminal (p95)": "Top 5% terminal value as a multiple of starting capital. The 'lottery' upside.",
    "P(loss)": "Probability the portfolio ends below the starting value across simulations.",
    "P(DD>50%)": "Probability of suffering at least a 50% drawdown at some point during the run. Anything > 5% is concerning.",
}


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
        "Best terminal (p95)": f"{m.best_case_terminal_p95:.2f}x",
        "P(loss)": f"{m.prob_loss*100:.1f}%",
        "P(DD>50%)": f"{m.prob_dd_over_50pct*100:.1f}%",
    }


def _interpret_metrics(portfolio: PortfolioResult) -> str:
    """Generate a 3-4 sentence plain-English read-out of the combined metrics."""
    m = portfolio.metrics_combined
    a, b = portfolio.metrics_a, portfolio.metrics_b
    pieces: list[str] = []

    # 1. Headline return / risk
    pieces.append(
        f'The combined portfolio compounds at <span class="kw-num">{m.cagr*100:.2f}%/yr</span> '
        f'with an annualised volatility of <span class="kw-num">{m.annualised_vol*100:.2f}%</span>.'
    )

    # 2. Sortino quality
    if m.sortino >= 2.0:
        sortino_q = ('<span class="kw-good">very strong</span> '
                     '(<span class="kw-num">&gt;= 2.0</span>) — solid enough to support '
                     'meaningful <span class="kw-concept">leverage</span>')
    elif m.sortino >= 1.0:
        sortino_q = ('<span class="kw-warn">decent</span> '
                     '(<span class="kw-num">1.0-2.0</span>) — usable but be cautious adding '
                     '<span class="kw-concept">leverage</span>')
    elif m.sortino >= 0:
        sortino_q = ('<span class="kw-bad">weak</span> '
                     '(<span class="kw-num">&lt;1.0</span>) — leverage will amplify '
                     '<span class="kw-bad">drawdowns</span> faster than returns')
    else:
        sortino_q = ('<span class="kw-bad">negative</span> — the strategy loses money on a '
                     'risk-adjusted basis')
    pieces.append(
        f'The <span class="kw-test">Sortino</span> of '
        f'<span class="kw-num">{m.sortino:.2f}</span> is {sortino_q}.'
    )

    # 3. Drawdown read-through
    if m.prob_dd_over_50pct > 0.10:
        dd_q = (f'More than <span class="kw-num">10%</span> of simulations breach a '
                f'<span class="kw-num">50%</span> drawdown '
                f'(<span class="kw-num">P(DD&gt;50%) = {m.prob_dd_over_50pct*100:.1f}%</span>) — '
                f'this is <span class="kw-bad">fragile</span>.')
    elif m.prob_dd_over_50pct > 0.02:
        dd_q = (f'A non-trivial <span class="kw-num">{m.prob_dd_over_50pct*100:.1f}%</span> of '
                f'simulations breach a <span class="kw-num">50%</span> drawdown — '
                f'<span class="kw-warn">survivable but uncomfortable</span>.')
    else:
        dd_q = (f'Only <span class="kw-num">{m.prob_dd_over_50pct*100:.1f}%</span> of simulations '
                f'breach a <span class="kw-num">50%</span> drawdown — '
                f'<span class="kw-good">tail risk looks contained</span>.')
    pieces.append(dd_q)

    # 4. Diversification benefit
    combined_better_than_avg = (
        m.sortino > 0.5 * (a.sortino + b.sortino) + 0.05
    )
    if combined_better_than_avg:
        pieces.append(
            'Combining the two sleeves produces a <span class="kw-good">better risk-adjusted result</span> '
            'than the simple average of the parts — <span class="kw-concept">diversification</span> '
            'is doing real work here.'
        )
    else:
        pieces.append(
            'Combining the two sleeves does <span class="kw-bad">not</span> improve risk-adjusted '
            'returns beyond their average — either <span class="kw-warn">correlation is too high</span> '
            'or one sleeve is dominating.'
        )

    # 5. Probability of loss
    if m.prob_loss > 0.40:
        pieces.append(
            f'<span class="kw-test">P(loss)</span> = <span class="kw-num">{m.prob_loss*100:.1f}%</span> '
            'is <span class="kw-bad">high</span> — re-examine inputs before allocating capital.'
        )
    elif m.prob_loss > 0.20:
        pieces.append(
            f'<span class="kw-test">P(loss)</span> = <span class="kw-num">{m.prob_loss*100:.1f}%</span> — '
            '<span class="kw-warn">meaningful chance of a losing run</span>.'
        )

    return " ".join(pieces)


# ---------------------------------------------------------------------------
def _section_dual_sleeve(
    close: pd.Series, results: dict, sb: controls.SidebarSettings,
    interval_seconds: float,
) -> tuple[BacktestResult, PortfolioResult, controls.SleeveAControls, controls.SleeveBControls]:
    with st.container(border=True):
        _section_open(
            "section-5", "05 / SECTION",
            "Dual-Sleeve Portfolio Backtest",
            '<span class="kw-concept">Sleeve A</span> is the <span class="kw-concept">demon engine</span> '
            'on your asset; <span class="kw-concept">Sleeve B</span> is a parametric '
            '<span class="kw-concept">crypto-leverage</span> book. Tune both, run '
            '<span class="kw-test">Monte Carlo</span>, and study the combined behaviour.',
        )

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
            weight=a_ctrl.weight, rebalance_rule=a_ctrl.rebalance_rule,
            time_period=a_ctrl.time_period,
            threshold_pct=a_ctrl.threshold_pct,
            band_sigma=a_ctrl.band_sigma,
            band_window=a_ctrl.band_window,
            cash_yield_pct=a_ctrl.cash_yield_pct,
            transaction_cost_bps=a_ctrl.transaction_cost_bps,
            interval_seconds=interval_seconds,
            annualisation=sb.annualisation,
        )

        if sb.annualisation == "calendar":
            ppy = (365.25 * 24 * 3600) / max(interval_seconds, 1.0)
        else:
            ppy = (cfg.DEFAULT_TRADING_HOURS_PER_YEAR * 3600) / max(interval_seconds, 1.0)
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
                horizon_periods=horizon, periods_per_year=ppy,
                student_t_df=cfg.SLEEVE_B_DEFAULTS.student_t_df,
                risk_free_rate_pct=sb.risk_free_rate_pct,
                mar_pct=sb.mar_pct,
                confidence_low_pct=sb.confidence_low,
                confidence_high_pct=sb.confidence_high,
            )

        with right:
            _subhead("Sleeve A historical equity",
                     desc="Demon equity curve generated by replaying your CSV through the rebalancer.")
            st.plotly_chart(charts.demon_equity_chart(bt, close), use_container_width=True)
            cols = st.columns(4)
            cols[0].metric("CAGR", f"{bt.cagr*100:.2f}%",
                           help="Compound annual growth rate of Sleeve A on the historical series.")
            cols[1].metric("Vol (ann.)", f"{bt.annualised_vol*100:.2f}%",
                           help="Annualised stdev of Sleeve A returns.")
            cols[2].metric("Max DD", f"{bt.max_drawdown*100:.2f}%",
                           help="Largest peak-to-trough loss over history.")
            cols[3].metric("Rebalances", f"{bt.n_rebalances}",
                           help="Number of rebalance events in the period.")

        st.markdown('<div class="subhead">Combined portfolio (Monte Carlo)</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="subhead-desc">Sleeve A bootstrapped, Sleeve B parametric, '
            'coupled by your correlation slider.</div>',
            unsafe_allow_html=True,
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            st.plotly_chart(charts.portfolio_equity_fan(portfolio,
                                                       sb.confidence_low,
                                                       sb.confidence_high),
                            use_container_width=True)
        with cc2:
            st.plotly_chart(charts.portfolio_drawdown_chart(portfolio),
                            use_container_width=True)

        cc3, cc4 = st.columns(2)
        with cc3:
            st.plotly_chart(charts.terminal_distribution(portfolio),
                            use_container_width=True)
        with cc4:
            st.plotly_chart(charts.sleeve_contribution_chart(portfolio),
                            use_container_width=True)

        # Metrics table — with hover tooltips per column
        _subhead("Metrics — by sleeve",
                 desc="Hover any column header for a definition. Read the interpretation below the table.")
        df_m = pd.DataFrame([
            _metrics_row("A (Demon)", portfolio.metrics_a),
            _metrics_row("B (Crypto leverage)", portfolio.metrics_b),
            _metrics_row("Combined", portfolio.metrics_combined),
        ])
        column_config = {
            col: st.column_config.Column(help=helptxt)
            for col, helptxt in _METRIC_HELP.items()
        }
        st.dataframe(df_m, use_container_width=True, hide_index=True,
                     column_config=column_config)

        # Inline glossary expander — for users who can't see the column header tooltip
        with st.expander("What does each metric mean?"):
            for col, helptxt in _METRIC_HELP.items():
                if col == "Sleeve":
                    continue
                st.markdown(f"**{col}** — {helptxt}")

        # Generated interpretation
        interp = _interpret_metrics(portfolio)
        st.markdown(f'<div class="interp-box">{interp}</div>', unsafe_allow_html=True)

        return bt, portfolio, a_ctrl, b_ctrl


# ---------------------------------------------------------------------------
def _section_alloc_optimiser(close: pd.Series, sb: controls.SidebarSettings,
                             a_ctrl: controls.SleeveAControls,
                             b_ctrl: controls.SleeveBControls,
                             interval_seconds: float) -> None:
    with st.container(border=True):
        _section_open(
            "section-6", "06 / SECTION",
            "Allocation Optimiser",
            'Sweeps <span class="kw-concept">Sleeve A</span> allocation '
            '<span class="kw-num">0-100%</span> in <span class="kw-num">5%</span> steps, runs a slimmer '
            '<span class="kw-test">Monte Carlo</span> at each step, and finds the mix with the '
            '<span class="kw-good">highest Sortino</span>. Click the button to run.',
        )
        if not st.button("Find optimal allocation", type="primary", key="opt_run"):
            return

        series_hash = _hash_series(close)
        bt = _cached_demon_backtest(
            series_hash=series_hash,
            close_values=tuple(close.to_numpy().tolist()),
            close_index=tuple(close.index),
            weight=a_ctrl.weight, rebalance_rule=a_ctrl.rebalance_rule,
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

        alloc_pcts = list(np.arange(0.0, 100.0 + cfg.ALLOC_SWEEP_STEP_PCT,
                                    cfg.ALLOC_SWEEP_STEP_PCT))
        cagrs, max_dds, sortinos = [], [], []
        n_mc_sweep = max(100, sb.n_simulations // 4)
        progress = st.progress(0.0, text="Sweeping allocations...")
        for i, a in enumerate(alloc_pcts):
            result = _cached_dual_sleeve(
                backtest_id=f"sweep_{series_hash}_{a}_{a_ctrl}_{b_ctrl}",
                sleeve_a_eq_values=eq_tuple,
                sleeve_a_alloc_pct=a, sleeve_b_alloc_pct=100.0 - a,
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
                horizon_periods=horizon, periods_per_year=ppy,
                student_t_df=cfg.SLEEVE_B_DEFAULTS.student_t_df,
                risk_free_rate_pct=sb.risk_free_rate_pct,
                mar_pct=sb.mar_pct,
                confidence_low_pct=sb.confidence_low,
                confidence_high_pct=sb.confidence_high,
            )
            cagrs.append(result.metrics_combined.cagr)
            max_dds.append(result.metrics_combined.max_drawdown)
            sortinos.append(result.metrics_combined.sortino)
            progress.progress((i + 1) / len(alloc_pcts),
                              text=f"Sweep {i+1}/{len(alloc_pcts)}")
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
            f"(Sortino = {sortinos[optimal_idx]:.2f}, "
            f"CAGR = {cagrs[optimal_idx]*100:.2f}%, "
            f"Max DD = {max_dds[optimal_idx]*100:.2f}%)"
        )


# ---------------------------------------------------------------------------
def _section_leverage(portfolio: PortfolioResult, sb: controls.SidebarSettings) -> None:
    with st.container(border=True):
        _section_open(
            "section-7", "07 / SECTION",
            "Leverage Sensitivity",
            'Applies <span class="kw-concept">leverage</span> to the combined portfolio\'s per-period '
            'returns minus <span class="kw-warn">borrow cost</span>. Shows where added gearing turns a '
            'clean strategy into a <span class="kw-bad">margin-call factory</span>.',
        )

        lev = st.slider("Leverage applied to combined portfolio (x)",
                        cfg.LEVERAGE_MIN, cfg.LEVERAGE_MAX,
                        1.0, cfg.LEVERAGE_STEP, key="lev_main")

        levs = list(np.arange(cfg.LEVERAGE_MIN,
                              cfg.LEVERAGE_MAX + cfg.LEVERAGE_STEP,
                              cfg.LEVERAGE_STEP))

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
        cols[0].metric(f"CAGR @ {lev}x", f"{cur_cagr*100:.2f}%",
                       help="Mean compound growth at this leverage level.")
        cols[1].metric(f"Max DD @ {lev}x", f"{cur_dd*100:.2f}%",
                       help="Mean max drawdown at this leverage level.")
        cols[2].metric(f"Sortino @ {lev}x", f"{cur_sort:.2f}",
                       help="Risk-adjusted return at this leverage level.")
        if cur_dd < -cfg.LEVERAGE_MARGIN_CALL_DD:
            st.error(f"Drawdown at {lev}x exceeds 50% — margin-call territory.")
        elif cur_dd < -cfg.LEVERAGE_DD_RED_THRESHOLD:
            st.warning(f"Drawdown at {lev}x exceeds 30%.")


# ---------------------------------------------------------------------------
def _section_conclusion(verdict: SuitabilityVerdict, portfolio: PortfolioResult) -> None:
    with st.container(border=True):
        _section_open(
            "section-8", "08 / SECTION",
            "Conclusion",
            'Aggregated <span class="kw-good">suitability score</span> '
            '(<span class="kw-num">0-100</span>), top reasons, suggested '
            '<span class="kw-concept">rebalance cadence</span>, max recommended '
            '<span class="kw-concept">leverage</span>, and any <span class="kw-bad">red flags</span>.',
        )
        _verdict_box(verdict)

        cols = st.columns(2)
        with cols[0]:
            st.markdown('<div class="subhead">Top 3 reasons</div>', unsafe_allow_html=True)
            for r in verdict.top_reasons:
                st.markdown(f"- {r}")
            st.markdown('<div class="subhead">Suggested rebalance frequency</div>',
                        unsafe_allow_html=True)
            st.markdown(f"> {verdict.suggested_rebalance}")
        with cols[1]:
            st.markdown('<div class="subhead">Risk envelope</div>', unsafe_allow_html=True)
            st.markdown(f"- Max recommended leverage: **{verdict.max_recommended_leverage}x**")
            st.markdown(
                f"- Combined Sortino achieved: **{portfolio.metrics_combined.sortino:.2f}** "
                "(rule of thumb: >= 2.0 to support meaningful leverage)"
            )
            st.markdown('<div class="subhead">Red flags</div>', unsafe_allow_html=True)
            if not verdict.red_flags:
                st.markdown("None detected.")
            else:
                for f in verdict.red_flags:
                    st.markdown(f"- {f}")

        with st.expander("Component score breakdown"):
            st.write(verdict.component_scores)


# ---------------------------------------------------------------------------
# Tab assembly
# ---------------------------------------------------------------------------
def render_analysis_tab() -> None:
    st.title("Shannon's Demon — Suitability Dashboard")
    st.caption(
        "Upload an OHLCV CSV, restrict to a date range if desired, run statistical "
        "mean-reversion tests, and stress-test a dual-sleeve portfolio (Demon + Crypto leverage) "
        "under Monte Carlo."
    )
    st.markdown(KW_LEGEND_HTML, unsafe_allow_html=True)

    sidebar = controls.render_settings_expander()

    upload_result = upload.render_uploader()
    if upload_result is None:
        st.info("Upload a CSV to begin. Required column: `close`.")
        return

    df = upload_result.df
    close = df["close"]

    # Date range filter (top of page, before any analysis)
    with st.container(border=True):
        filtered = _render_date_filter(close, upload_result.has_time_index)
    if filtered is None or len(filtered) < cfg.MIN_OBS_HARD_BLOCK:
        return
    close = filtered

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
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    controls.render_sidebar_toc()

    tab_analysis, tab_docs, tab_assumptions = st.tabs(
        ["Analysis", "Documentation", "Assumptions & Limitations"]
    )
    with tab_analysis:
        render_analysis_tab()
    with tab_docs:
        docs.render_documentation_tab()
    with tab_assumptions:
        docs.render_assumptions_tab()


if __name__ == "__main__":
    main()
