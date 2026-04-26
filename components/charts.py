"""Plotly chart builders. Pure functions returning go.Figure — no Streamlit calls.

All charts use a unified dark institutional palette set in `config.PLOTLY_DEFAULTS`.
"""

from __future__ import annotations

import copy
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config as cfg
from analysis.backtest import BacktestResult
from analysis.portfolio import PortfolioResult
from analysis.stats_tests import HarvestResult, HurstResult, RegimeResult, VolatilityResult


# ---------------------------------------------------------------------------
def _apply_theme(fig: go.Figure, height: int = 360, **overrides) -> go.Figure:
    """Apply dark quant theme to a figure, then layer in overrides."""
    base = copy.deepcopy(cfg.PLOTLY_DEFAULTS)
    base["height"] = height
    base["margin"] = dict(l=10, r=10, t=40, b=10)
    base["hovermode"] = "x unified"
    fig.update_layout(**base)
    if overrides:
        fig.update_layout(**overrides)
    return fig


# ---------------------------------------------------------------------------
def price_overview(close: pd.Series, window: int = 90) -> go.Figure:
    """Close + rolling mean + +/-1 sigma / +/-2 sigma bands."""
    rm = close.rolling(window, min_periods=max(10, window // 3)).mean()
    rs = close.rolling(window, min_periods=max(10, window // 3)).std()
    upper1, lower1 = rm + rs, rm - rs
    upper2, lower2 = rm + 2 * rs, rm - 2 * rs

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=upper2, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=close.index, y=lower2, line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(88,166,255,0.08)", name="+/-2 sigma band"))
    fig.add_trace(go.Scatter(x=close.index, y=upper1, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=close.index, y=lower1, line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(88,166,255,0.18)", name="+/-1 sigma band"))
    fig.add_trace(go.Scatter(x=close.index, y=rm, line=dict(color=cfg.THEME_ACCENT, width=1.4),
                             name=f"Rolling mean ({window})"))
    fig.add_trace(go.Scatter(x=close.index, y=close, line=dict(color=cfg.THEME_TEXT, width=1.1),
                             name="Close"))

    return _apply_theme(fig, height=420, xaxis_title="Time", yaxis_title="Price")


# ---------------------------------------------------------------------------
def hurst_gauge(h: HurstResult) -> go.Figure:
    """Horizontal gauge for the Hurst exponent on 0-1 with shaded zones."""
    val = h.best_estimate if np.isfinite(h.best_estimate) else 0.5
    fig = go.Figure()

    fig.add_shape(type="rect", x0=0, x1=0.45, y0=0, y1=1,
                  fillcolor="rgba(63,185,80,0.18)", line_width=0)
    fig.add_shape(type="rect", x0=0.45, x1=0.55, y0=0, y1=1,
                  fillcolor="rgba(210,153,34,0.18)", line_width=0)
    fig.add_shape(type="rect", x0=0.55, x1=1.0, y0=0, y1=1,
                  fillcolor="rgba(218,54,51,0.18)", line_width=0)

    fig.add_trace(go.Scatter(
        x=[val], y=[0.5], mode="markers+text",
        marker=dict(size=20, color=cfg.THEME_ACCENT, symbol="diamond",
                    line=dict(color=cfg.THEME_TEXT, width=1.5)),
        text=[f"H={val:.3f}"], textposition="top center",
        textfont=dict(color=cfg.THEME_TEXT, size=12),
        showlegend=False,
    ))

    if np.isfinite(h.rs_hurst):
        fig.add_vline(x=h.rs_hurst, line_dash="dot", line_color=cfg.THEME_TEXT_MUTED,
                      annotation_text="R/S", annotation_position="bottom",
                      annotation_font_color=cfg.THEME_TEXT_MUTED)
    if np.isfinite(h.var_hurst):
        fig.add_vline(x=h.var_hurst, line_dash="dash", line_color=cfg.THEME_TEXT_MUTED,
                      annotation_text="Var", annotation_position="top",
                      annotation_font_color=cfg.THEME_TEXT_MUTED)

    fig = _apply_theme(fig, height=180,
                       xaxis=dict(range=[0, 1], title="Hurst exponent", gridcolor=cfg.THEME_GRID),
                       yaxis=dict(visible=False, range=[0, 1]),
                       showlegend=False, hovermode=False)
    fig.add_annotation(x=0.225, y=1.05, text="Mean reverting", showarrow=False,
                       xref="x", yref="paper", font=dict(color=cfg.THEME_TEXT_MUTED, size=11))
    fig.add_annotation(x=0.50, y=1.05, text="Random walk", showarrow=False,
                       xref="x", yref="paper", font=dict(color=cfg.THEME_TEXT_MUTED, size=11))
    fig.add_annotation(x=0.775, y=1.05, text="Trending", showarrow=False,
                       xref="x", yref="paper", font=dict(color=cfg.THEME_TEXT_MUTED, size=11))
    return fig


# ---------------------------------------------------------------------------
def regime_chart(close: pd.Series, r: RegimeResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close, name="Close",
                             line=dict(color=cfg.THEME_TEXT, width=1)))
    if not r.rolling_mean.empty:
        fig.add_trace(go.Scatter(x=r.rolling_mean.index, y=r.rolling_mean, name="Rolling mean",
                                 line=dict(color=cfg.THEME_ACCENT, width=1.4)))
    if not r.expanding_mean.empty:
        fig.add_trace(go.Scatter(x=r.expanding_mean.index, y=r.expanding_mean, name="Expanding mean",
                                 line=dict(color=cfg.THEME_TEAL, width=1, dash="dot")))

    for i in r.shift_indices:
        if 0 <= i < len(close):
            fig.add_vline(x=close.index[i], line_color=cfg.THEME_DANGER,
                          line_dash="dash", opacity=0.55)

    return _apply_theme(fig, height=360, xaxis_title="Time", yaxis_title="Close")


# ---------------------------------------------------------------------------
def volatility_chart(v: VolatilityResult) -> go.Figure:
    fig = go.Figure()
    if not v.rolling_30p_annualised.empty:
        fig.add_trace(go.Scatter(
            x=v.rolling_30p_annualised.index,
            y=v.rolling_30p_annualised * 100,
            name="Rolling 30p ann. vol",
            line=dict(color=cfg.THEME_INFO, width=1.4),
        ))
    if np.isfinite(v.full_sample_annualised):
        fig.add_hline(y=v.full_sample_annualised * 100, line_dash="dash",
                      line_color=cfg.THEME_ACCENT,
                      annotation_text=f"Full sample: {v.full_sample_annualised*100:.1f}%",
                      annotation_font_color=cfg.THEME_ACCENT)
    return _apply_theme(fig, height=320, xaxis_title="Time",
                        yaxis_title="Annualised volatility (%)")


# ---------------------------------------------------------------------------
def harvest_curve(h: HarvestResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=h.curve_w, y=h.curve_bonus,
        line=dict(color=cfg.THEME_SUCCESS, width=2),
        name="Bonus(w)",
        hovertemplate="w=%{x:.2f}<br>bonus=%{y:.3f}%/yr<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[h.weight], y=[h.bonus_pct], mode="markers+text",
        marker=dict(size=14, color=cfg.THEME_ACCENT, symbol="x",
                    line=dict(color=cfg.THEME_TEXT, width=2)),
        text=[f"{h.bonus_pct:.3f}%/yr"], textposition="top center",
        textfont=dict(color=cfg.THEME_TEXT),
        name="Your w",
    ))
    return _apply_theme(fig, height=320,
                        xaxis_title="Weight in risky asset (w)",
                        yaxis_title="Annualised rebalancing bonus (%)")


# ---------------------------------------------------------------------------
def demon_equity_chart(bt: BacktestResult, close: pd.Series) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.55, 0.45],
                        subplot_titles=["Sleeve A equity", "Underlying price + rebalance events"])

    fig.add_trace(go.Scatter(x=bt.equity_curve.index, y=bt.equity_curve, name="Equity",
                             line=dict(color=cfg.THEME_SUCCESS, width=1.6)), row=1, col=1)
    fig.add_trace(go.Scatter(x=close.index, y=close, name="Close",
                             line=dict(color=cfg.THEME_TEXT, width=1)), row=2, col=1)

    rb_idx = [close.index[i] for i in bt.rebalance_events if 0 <= i < len(close)]
    rb_y = [close.iloc[i] for i in bt.rebalance_events if 0 <= i < len(close)]
    if rb_idx:
        fig.add_trace(go.Scatter(x=rb_idx, y=rb_y, mode="markers", name="Rebalance",
                                 marker=dict(color=cfg.THEME_ACCENT, size=6, symbol="triangle-up",
                                             line=dict(color=cfg.THEME_BG, width=0.5))),
                      row=2, col=1)

    fig = _apply_theme(fig, height=520)
    fig.update_yaxes(title_text="Equity", row=1, col=1, gridcolor=cfg.THEME_GRID)
    fig.update_yaxes(title_text="Price", row=2, col=1, gridcolor=cfg.THEME_GRID)
    fig.update_xaxes(gridcolor=cfg.THEME_GRID)
    # subplot titles colour
    for ann in fig.layout.annotations:
        ann.font = dict(color=cfg.THEME_ACCENT, size=12)
    return fig


# ---------------------------------------------------------------------------
def portfolio_equity_fan(pr: PortfolioResult, low_pct: int, high_pct: int) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pr.time_index, y=pr.combined_p_high,
                             line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=pr.time_index, y=pr.combined_p_low,
                             line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(63,185,80,0.18)",
                             name=f"P{low_pct}-P{high_pct}"))
    fig.add_trace(go.Scatter(x=pr.time_index, y=pr.combined_p50,
                             line=dict(color=cfg.THEME_SUCCESS, width=2),
                             name="Median"))
    fig.add_trace(go.Scatter(x=pr.time_index, y=pr.combined_mean,
                             line=dict(color=cfg.THEME_ACCENT, width=1.4, dash="dash"),
                             name="Mean"))
    return _apply_theme(fig, height=420, xaxis_title="Period",
                        yaxis_title="Combined portfolio value (start = 1)")


def portfolio_drawdown_chart(pr: PortfolioResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pr.time_index, y=pr.drawdown_mean * 100,
                             name="Mean drawdown",
                             line=dict(color=cfg.THEME_WARNING), fill="tozeroy",
                             fillcolor="rgba(210,153,34,0.18)"))
    fig.add_trace(go.Scatter(x=pr.time_index, y=pr.drawdown_worst * 100,
                             name="Worst-case drawdown",
                             line=dict(color=cfg.THEME_DANGER, dash="dash")))
    return _apply_theme(fig, height=320, xaxis_title="Period",
                        yaxis_title="Drawdown (%)")


def terminal_distribution(pr: PortfolioResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=pr.terminal_values_combined, nbinsx=50,
        marker_color=cfg.THEME_INFO, opacity=0.85,
        marker_line=dict(color=cfg.THEME_BORDER, width=0.4),
        name="Combined",
    ))
    fig.add_vline(x=1.0, line_dash="dash", line_color=cfg.THEME_TEXT_MUTED,
                  annotation_text="Break-even",
                  annotation_font_color=cfg.THEME_TEXT_MUTED)
    fig.add_vline(x=float(np.median(pr.terminal_values_combined)),
                  line_dash="dot", line_color=cfg.THEME_ACCENT,
                  annotation_text=f"Median {np.median(pr.terminal_values_combined):.2f}",
                  annotation_font_color=cfg.THEME_ACCENT)
    return _apply_theme(fig, height=320,
                        xaxis_title="Terminal value (x starting capital)",
                        yaxis_title="Simulation count",
                        hovermode="x")


def sleeve_contribution_chart(pr: PortfolioResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.sleeve_a_contribution,
        name="Sleeve A (Demon)", line=dict(width=0),
        stackgroup="one", fillcolor="rgba(63,185,80,0.55)",
    ))
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.sleeve_b_contribution,
        name="Sleeve B (Crypto leverage)", line=dict(width=0),
        stackgroup="one", fillcolor="rgba(163,113,247,0.55)",
    ))
    return _apply_theme(fig, height=320, xaxis_title="Period",
                        yaxis_title="Allocation-weighted value")


# ---------------------------------------------------------------------------
def allocation_optimiser_chart(
    alloc_pcts: list[float],
    cagrs: list[float],
    max_dds: list[float],
    sortinos: list[float],
    current_alloc: float,
    optimal_alloc: float,
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=alloc_pcts, y=[c * 100 for c in cagrs],
                             line=dict(color=cfg.THEME_SUCCESS, width=2),
                             mode="lines+markers", name="CAGR (%)"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=alloc_pcts, y=[d * 100 for d in max_dds],
                             line=dict(color=cfg.THEME_DANGER, width=2, dash="dash"),
                             mode="lines+markers", name="Max drawdown (%)"),
                  secondary_y=True)
    fig.add_trace(go.Scatter(x=alloc_pcts, y=sortinos,
                             line=dict(color=cfg.THEME_INFO, width=1.2, dash="dot"),
                             mode="lines", name="Sortino", visible="legendonly"),
                  secondary_y=False)

    fig.add_vline(x=current_alloc, line_color=cfg.THEME_TEXT_MUTED, line_dash="dot",
                  annotation_text="Current", annotation_font_color=cfg.THEME_TEXT_MUTED)
    fig.add_vline(x=optimal_alloc, line_color=cfg.THEME_ACCENT, line_dash="dash",
                  annotation_text="Optimal Sortino", annotation_font_color=cfg.THEME_ACCENT)

    fig = _apply_theme(fig, height=420, xaxis_title="Sleeve A allocation (%)")
    fig.update_yaxes(title_text="CAGR (%)", secondary_y=False, gridcolor=cfg.THEME_GRID)
    fig.update_yaxes(title_text="Max drawdown (%)", secondary_y=True, gridcolor=cfg.THEME_GRID)
    return fig


def leverage_sensitivity_chart(
    leverages: list[float],
    cagrs: list[float],
    max_dds: list[float],
    sortinos: list[float],
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = [cfg.THEME_SUCCESS if d > -0.30 else cfg.THEME_DANGER for d in max_dds]

    fig.add_trace(go.Bar(x=leverages, y=[c * 100 for c in cagrs],
                         marker_color=colors, name="Levered CAGR (%)",
                         marker_line=dict(color=cfg.THEME_BORDER, width=0.5)),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=leverages, y=[d * 100 for d in max_dds],
                             line=dict(color=cfg.THEME_DANGER, width=2, dash="dash"),
                             mode="lines+markers", name="Levered max DD (%)"),
                  secondary_y=True)
    fig.add_trace(go.Scatter(x=leverages, y=sortinos,
                             line=dict(color=cfg.THEME_INFO, width=1.5),
                             mode="lines+markers", name="Levered Sortino",
                             visible="legendonly"),
                  secondary_y=False)

    fig = _apply_theme(fig, height=380, xaxis_title="Leverage (x)")
    fig.update_yaxes(title_text="CAGR (%)", secondary_y=False, gridcolor=cfg.THEME_GRID)
    fig.update_yaxes(title_text="Max drawdown (%)", secondary_y=True, gridcolor=cfg.THEME_GRID)
    return fig
