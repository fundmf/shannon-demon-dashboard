"""Plotly chart builders. Pure functions returning go.Figure — no Streamlit calls."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis.backtest import BacktestResult
from analysis.portfolio import PortfolioResult
from analysis.stats_tests import HarvestResult, HurstResult, RegimeResult, VolatilityResult


# ---------------------------------------------------------------------------
def price_overview(close: pd.Series, window: int = 90) -> go.Figure:
    """Close + rolling mean + ±1σ/±2σ Bollinger-style bands."""
    rm = close.rolling(window, min_periods=max(10, window // 3)).mean()
    rs = close.rolling(window, min_periods=max(10, window // 3)).std()
    upper1, lower1 = rm + rs, rm - rs
    upper2, lower2 = rm + 2 * rs, rm - 2 * rs

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=upper2, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=close.index, y=lower2, line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(99,110,250,0.10)", name="±2σ band"))
    fig.add_trace(go.Scatter(x=close.index, y=upper1, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=close.index, y=lower1, line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(99,110,250,0.20)", name="±1σ band"))
    fig.add_trace(go.Scatter(x=close.index, y=rm, line=dict(color="orange", width=1.5), name=f"Rolling mean ({window})"))
    fig.add_trace(go.Scatter(x=close.index, y=close, line=dict(color="#1f77b4", width=1.2), name="Close"))

    fig.update_layout(
        height=420, hovermode="x unified",
        xaxis_title="Time", yaxis_title="Price",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
def hurst_gauge(h: HurstResult) -> go.Figure:
    """Horizontal gauge for the Hurst exponent on 0-1 with shaded zones."""
    val = h.best_estimate if np.isfinite(h.best_estimate) else 0.5
    fig = go.Figure()

    # Coloured zones
    fig.add_shape(type="rect", x0=0, x1=0.45, y0=0, y1=1, fillcolor="rgba(46,204,113,0.25)", line_width=0)
    fig.add_shape(type="rect", x0=0.45, x1=0.55, y0=0, y1=1, fillcolor="rgba(241,196,15,0.25)", line_width=0)
    fig.add_shape(type="rect", x0=0.55, x1=1.0, y0=0, y1=1, fillcolor="rgba(231,76,60,0.25)", line_width=0)

    # Marker
    fig.add_trace(go.Scatter(
        x=[val], y=[0.5], mode="markers+text",
        marker=dict(size=20, color="black", symbol="diamond"),
        text=[f"H={val:.3f}"], textposition="top center",
        showlegend=False,
    ))

    # Reference lines for both estimators
    if np.isfinite(h.rs_hurst):
        fig.add_vline(x=h.rs_hurst, line_dash="dot", line_color="#2c3e50",
                      annotation_text="R/S", annotation_position="bottom")
    if np.isfinite(h.var_hurst):
        fig.add_vline(x=h.var_hurst, line_dash="dash", line_color="#7f8c8d",
                      annotation_text="Var", annotation_position="top")

    fig.update_layout(
        height=180, xaxis=dict(range=[0, 1], title="Hurst exponent"),
        yaxis=dict(visible=False, range=[0, 1]),
        margin=dict(l=10, r=10, t=30, b=30), showlegend=False,
    )
    fig.add_annotation(x=0.225, y=1.05, text="Mean reverting", showarrow=False, xref="x", yref="paper")
    fig.add_annotation(x=0.50, y=1.05, text="Random walk", showarrow=False, xref="x", yref="paper")
    fig.add_annotation(x=0.775, y=1.05, text="Trending", showarrow=False, xref="x", yref="paper")
    return fig


# ---------------------------------------------------------------------------
def regime_chart(close: pd.Series, r: RegimeResult) -> go.Figure:
    """Close with rolling/expanding mean and shift markers."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close, name="Close", line=dict(color="#1f77b4", width=1)))
    if not r.rolling_mean.empty:
        fig.add_trace(go.Scatter(x=r.rolling_mean.index, y=r.rolling_mean, name="Rolling mean",
                                 line=dict(color="orange", width=1.5)))
    if not r.expanding_mean.empty:
        fig.add_trace(go.Scatter(x=r.expanding_mean.index, y=r.expanding_mean, name="Expanding mean",
                                 line=dict(color="green", width=1, dash="dot")))

    for i in r.shift_indices:
        if 0 <= i < len(close):
            fig.add_vline(x=close.index[i], line_color="red", line_dash="dash", opacity=0.6)

    fig.update_layout(
        height=360, hovermode="x unified",
        xaxis_title="Time", yaxis_title="Close",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
def volatility_chart(v: VolatilityResult) -> go.Figure:
    """Rolling 30p annualised vol with full-sample reference line."""
    fig = go.Figure()
    if not v.rolling_30p_annualised.empty:
        fig.add_trace(go.Scatter(
            x=v.rolling_30p_annualised.index,
            y=v.rolling_30p_annualised * 100,
            name="Rolling 30p ann. vol", line=dict(color="#2980b9"),
        ))
    if np.isfinite(v.full_sample_annualised):
        fig.add_hline(y=v.full_sample_annualised * 100, line_dash="dash",
                      line_color="orange",
                      annotation_text=f"Full sample: {v.full_sample_annualised*100:.1f}%")
    fig.update_layout(
        height=320, hovermode="x unified",
        xaxis_title="Time", yaxis_title="Annualised volatility (%)",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
def harvest_curve(h: HarvestResult) -> go.Figure:
    """Shannon harvest bonus vs weight w with the user's pick marked."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=h.curve_w, y=h.curve_bonus,
        line=dict(color="#27ae60", width=2),
        name="Bonus(w)",
        hovertemplate="w=%{x:.2f}<br>bonus=%{y:.3f}%/yr<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[h.weight], y=[h.bonus_pct], mode="markers+text",
        marker=dict(size=14, color="red", symbol="x"),
        text=[f"{h.bonus_pct:.3f}%/yr"], textposition="top center",
        name="Your w",
    ))
    fig.update_layout(
        height=320, hovermode="x unified",
        xaxis_title="Weight in risky asset (w)",
        yaxis_title="Annualised rebalancing bonus (%)",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
def demon_equity_chart(bt: BacktestResult, close: pd.Series) -> go.Figure:
    """Two-panel: equity curve + price with rebalance markers."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.55, 0.45],
                        subplot_titles=["Sleeve A equity", "Underlying price + rebalance events"])

    fig.add_trace(go.Scatter(x=bt.equity_curve.index, y=bt.equity_curve, name="Equity",
                             line=dict(color="#27ae60")), row=1, col=1)
    fig.add_trace(go.Scatter(x=close.index, y=close, name="Close",
                             line=dict(color="#1f77b4", width=1)), row=2, col=1)

    rb_idx = [close.index[i] for i in bt.rebalance_events if 0 <= i < len(close)]
    rb_y = [close.iloc[i] for i in bt.rebalance_events if 0 <= i < len(close)]
    if rb_idx:
        fig.add_trace(go.Scatter(x=rb_idx, y=rb_y, mode="markers", name="Rebalance",
                                 marker=dict(color="red", size=6, symbol="triangle-up")), row=2, col=1)

    fig.update_layout(height=520, hovermode="x unified",
                      margin=dict(l=10, r=10, t=40, b=10))
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Price", row=2, col=1)
    return fig


# ---------------------------------------------------------------------------
def portfolio_equity_fan(pr: PortfolioResult, low_pct: int, high_pct: int) -> go.Figure:
    """Mean equity curve with confidence band + median."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.combined_p_high,
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.combined_p_low,
        line=dict(width=0), fill="tonexty",
        fillcolor="rgba(46,204,113,0.20)",
        name=f"P{low_pct}–P{high_pct}",
    ))
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.combined_p50,
        line=dict(color="#27ae60", width=2),
        name="Median",
    ))
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.combined_mean,
        line=dict(color="#2c3e50", width=1.5, dash="dash"),
        name="Mean",
    ))
    fig.update_layout(
        height=420, hovermode="x unified",
        xaxis_title="Period", yaxis_title="Combined portfolio value (start = 1)",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


def portfolio_drawdown_chart(pr: PortfolioResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.drawdown_mean * 100, name="Mean drawdown",
        line=dict(color="#e67e22"), fill="tozeroy",
        fillcolor="rgba(230,126,34,0.20)",
    ))
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.drawdown_worst * 100, name="Worst-case drawdown",
        line=dict(color="#c0392b", dash="dash"),
    ))
    fig.update_layout(
        height=320, hovermode="x unified",
        xaxis_title="Period", yaxis_title="Drawdown (%)",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


def terminal_distribution(pr: PortfolioResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=pr.terminal_values_combined, nbinsx=50,
        marker_color="#27ae60", opacity=0.8,
        name="Combined",
    ))
    fig.add_vline(x=1.0, line_dash="dash", line_color="black",
                  annotation_text="Break-even")
    fig.add_vline(
        x=float(np.median(pr.terminal_values_combined)),
        line_dash="dot", line_color="orange",
        annotation_text=f"Median {np.median(pr.terminal_values_combined):.2f}",
    )
    fig.update_layout(
        height=320,
        xaxis_title="Terminal value (× starting capital)",
        yaxis_title="Simulation count",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


def sleeve_contribution_chart(pr: PortfolioResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.sleeve_a_contribution,
        name="Sleeve A (Demon)", line=dict(width=0),
        stackgroup="one", fillcolor="rgba(46,204,113,0.55)",
    ))
    fig.add_trace(go.Scatter(
        x=pr.time_index, y=pr.sleeve_b_contribution,
        name="Sleeve B (Crypto leverage)", line=dict(width=0),
        stackgroup="one", fillcolor="rgba(155,89,182,0.55)",
    ))
    fig.update_layout(
        height=320, hovermode="x unified",
        xaxis_title="Period", yaxis_title="Allocation-weighted value",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
def allocation_optimiser_chart(
    alloc_pcts: list[float],
    cagrs: list[float],
    max_dds: list[float],
    sortinos: list[float],
    current_alloc: float,
    optimal_alloc: float,
) -> go.Figure:
    """X-axis: Sleeve A %, twin Y: CAGR (left), max DD (right). Markers for current vs optimal."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=alloc_pcts, y=[c * 100 for c in cagrs],
        line=dict(color="#27ae60", width=2),
        mode="lines+markers", name="CAGR (%)",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=alloc_pcts, y=[d * 100 for d in max_dds],
        line=dict(color="#c0392b", width=2, dash="dash"),
        mode="lines+markers", name="Max drawdown (%)",
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=alloc_pcts, y=sortinos,
        line=dict(color="#2980b9", width=1.2, dash="dot"),
        mode="lines", name="Sortino", yaxis="y3",
        visible="legendonly",
    ), secondary_y=False)

    fig.add_vline(x=current_alloc, line_color="black", line_dash="dot",
                  annotation_text="Current")
    fig.add_vline(x=optimal_alloc, line_color="purple", line_dash="dash",
                  annotation_text="Optimal Sortino")

    fig.update_layout(
        height=420, hovermode="x unified",
        xaxis_title="Sleeve A allocation (%)",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.update_yaxes(title_text="CAGR (%)", secondary_y=False)
    fig.update_yaxes(title_text="Max drawdown (%)", secondary_y=True)
    return fig


def leverage_sensitivity_chart(
    leverages: list[float],
    cagrs: list[float],
    max_dds: list[float],
    sortinos: list[float],
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["#27ae60" if d > -0.30 else "#c0392b" for d in max_dds]

    fig.add_trace(go.Bar(
        x=leverages, y=[c * 100 for c in cagrs],
        marker_color=colors, name="Levered CAGR (%)",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=leverages, y=[d * 100 for d in max_dds],
        line=dict(color="#c0392b", width=2, dash="dash"),
        mode="lines+markers", name="Levered max DD (%)",
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=leverages, y=sortinos,
        line=dict(color="#2980b9", width=1.5),
        mode="lines+markers", name="Levered Sortino",
        visible="legendonly",
    ), secondary_y=False)

    fig.update_layout(
        height=380, hovermode="x unified",
        xaxis_title="Leverage (×)",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.update_yaxes(title_text="CAGR (%)", secondary_y=False)
    fig.update_yaxes(title_text="Max drawdown (%)", secondary_y=True)
    return fig
