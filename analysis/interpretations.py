"""Plain-English interpretations + overall suitability scoring.

Each interpret_* function takes a result dataclass and returns a 2-3 sentence
narrative aimed at a numerate but non-statistical reader.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import config as cfg
from analysis.stats_tests import (
    ADFResult,
    HalfLifeResult,
    HarvestResult,
    HurstResult,
    KPSSResult,
    RegimeResult,
    VolatilityResult,
)


Verdict = Literal["strong", "marginal", "weak", "unsuitable"]


@dataclass
class SuitabilityVerdict:
    """Overall suitability assessment."""

    score: int                          # 0-100
    verdict: Verdict
    color: str                          # 'green' | 'amber' | 'red'
    headline: str                       # one-line summary
    top_reasons: list[str]              # top 3 drivers
    red_flags: list[str]
    suggested_rebalance: str
    max_recommended_leverage: float
    component_scores: dict[str, int]


# ---------------------------------------------------------------------------
def interpret_adf(r: ADFResult) -> str:
    if r.status == "error":
        return f"ADF could not be computed ({r.error})."
    base = f"ADF p-value (constant only) = {r.pvalue_c:.4f}."
    if r.status == "pass":
        out = (
            f"{base} The series rejects the unit-root null at the 5% level — "
            "evidence of mean reversion around a stable level."
        )
    elif r.status == "marginal":
        out = (
            f"{base} The result sits between 5% and 10% — weak evidence of mean "
            "reversion. Treat with caution and look at the half-life and Hurst values."
        )
    else:
        out = (
            f"{base} The series fails to reject the unit-root null — it behaves "
            "like a random walk and is unlikely to mean-revert reliably."
        )

    diverge = abs(r.pvalue_c - r.pvalue_ct) > 0.05
    if diverge:
        out += (
            f" Note: with constant + trend the p-value is {r.pvalue_ct:.4f}, suggesting "
            "a possible deterministic trend component."
        )
    return out


def interpret_kpss(r: KPSSResult) -> str:
    if r.status == "error":
        return f"KPSS could not be computed ({r.error})."
    base = f"KPSS p-value = {r.pvalue:.4f}."
    if r.status == "pass":
        out = (
            f"{base} KPSS fails to reject level-stationarity — consistent with a "
            "stable mean over time."
        )
    else:
        out = (
            f"{base} KPSS rejects level-stationarity — the mean appears to drift, "
            "so any rebalancing target should be a moving reference rather than a fixed level."
        )
    if r.boundary_warning:
        out += " (KPSS p-value is at the table boundary; treat as approximate.)"
    return out


def interpret_hurst(r: HurstResult) -> str:
    if r.status == "error":
        return f"Hurst could not be computed ({r.error})."
    h = r.best_estimate
    if r.status == "pass":
        out = (
            f"Hurst ≈ {h:.3f} — anti-persistent. The series is mean-reverting, "
            "which is exactly what you want for a Shannon's Demon engine."
        )
    elif r.status == "marginal":
        out = (
            f"Hurst ≈ {h:.3f} — close to a random walk. Rebalancing alpha is fragile; "
            "transaction costs may eat the harvest."
        )
    else:
        out = (
            f"Hurst ≈ {h:.3f} — persistent / trending. Mean-reversion is unlikely, "
            "and rebalancing this asset will probably hurt rather than help."
        )
    if r.inconsistent:
        out += (
            f" (R/S = {r.rs_hurst:.3f} vs variance method = {r.var_hurst:.3f} — methods disagree, "
            "the estimate is noisy on this sample.)"
        )
    return out


def interpret_half_life(r: HalfLifeResult) -> str:
    if r.status == "error":
        return f"Half-life could not be computed ({r.error})."
    if r.status == "fail":
        return (
            f"AR(1) coefficient β = {r.beta:.4f} (p = {r.beta_pvalue:.3f}). "
            "There is no statistically significant pull back to the mean — half-life is undefined."
        )
    return (
        f"AR(1) β = {r.beta:.4f} (p = {r.beta_pvalue:.3f}). Half-life of mean reversion ≈ "
        f"{r.half_life_periods:.1f} periods ({r.half_life_human}). "
        f"Aim to rebalance every {r.suggested_rebalance_min_periods:.0f}–"
        f"{r.suggested_rebalance_max_periods:.0f} periods (0.5×–1× the half-life)."
    )


def interpret_regime(r: RegimeResult) -> str:
    if r.status == "error":
        return f"Regime detection could not be computed ({r.error})."
    method = "PELT change-point" if r.method == "pelt" else "rolling-mean heuristic"
    if r.status == "pass":
        out = f"{r.n_shifts} regime shift(s) detected via {method}. The mean is stable enough that a single rebalancing target should hold."
    elif r.status == "marginal":
        out = f"{r.n_shifts} regime shifts detected ({method}). The mean drifts occasionally — consider a rolling-window rebalance target."
    else:
        out = f"{r.n_shifts} regime shifts detected ({method}). The series is structurally unstable; a fixed mean-reversion target will be wrong most of the time."
    return out


def interpret_volatility(r: VolatilityResult) -> str:
    if r.status == "error":
        return f"Volatility could not be computed ({r.error})."
    full = r.full_sample_annualised * 100
    if r.status == "pass":
        out = f"Annualised volatility = {full:.1f}% — squarely in the Shannon harvesting sweet spot (5–30%)."
    elif full * 0.01 < cfg.VOL_LOW_BAND:
        out = f"Annualised volatility = {full:.1f}% — too quiet to generate meaningful rebalancing alpha after costs."
    else:
        out = f"Annualised volatility = {full:.1f}% — high harvesting potential, but tail-risk and execution slippage become material."
    if r.realised_30p_annualised and r.realised_30p_annualised > 0:
        recent = r.realised_30p_annualised * 100
        out += f" Recent 30-period realised vol ≈ {recent:.1f}%."
    return out


# ---------------------------------------------------------------------------
def combined_stationarity_verdict(adf: ADFResult, kpss_r: KPSSResult) -> tuple[str, str]:
    """Return (banner_text, color) summarising the ADF+KPSS combination."""
    a_pass = adf.status == "pass"
    k_pass = kpss_r.status == "pass"
    if a_pass and k_pass:
        return (
            "Strongly stationary / mean-reverting — both ADF and KPSS agree the series has a stable mean. Ideal for Shannon's Demon.",
            "green",
        )
    if a_pass and not k_pass:
        return (
            "Difference-stationary — ADF accepts mean reversion but KPSS rejects level-stationarity. Mean reverts around a shifting level; use a rolling reference, not a fixed one.",
            "amber",
        )
    if not a_pass and k_pass:
        return (
            "Trend-stationary — reverts around a deterministic trend rather than a fixed level. Consider detrending before applying a demon strategy.",
            "amber",
        )
    return (
        "Non-stationary — neither test supports mean reversion. Unsuitable for a fixed-target rebalancing strategy.",
        "red",
    )


# ---------------------------------------------------------------------------
def _score_component(status: str) -> int:
    return {"pass": 100, "marginal": 60, "fail": 20, "error": 0}.get(status, 0)


def overall_suitability(
    adf: ADFResult,
    kpss_r: KPSSResult,
    hurst: HurstResult,
    hl: HalfLifeResult,
    regime: RegimeResult,
    vol: VolatilityResult,
) -> SuitabilityVerdict:
    """Aggregate component scores into a 0-100 verdict.

    Weights live in config.SCORE_WEIGHTS. Each test contributes its weighted
    component score; the sum is normalised against total possible weight.
    """
    components = {
        "adf": _score_component(adf.status),
        "kpss": _score_component(kpss_r.status),
        "hurst": _score_component(hurst.status),
        "half_life": _score_component(hl.status),
        "regime_stability": _score_component(regime.status),
        "vol_band": _score_component(vol.status),
    }
    weights = cfg.SCORE_WEIGHTS
    total_weight = sum(weights.values())
    weighted = sum(components[k] * weights[k] for k in components) / total_weight
    score = int(round(weighted))

    if score >= cfg.VERDICT_STRONG_MIN:
        verdict, color = "strong", "green"
        headline = "Strong fit for a Shannon's Demon engine. The series is mean-reverting with adequate volatility for harvesting."
    elif score >= cfg.VERDICT_MARGINAL_MIN:
        verdict, color = "marginal", "amber"
        headline = "Marginal fit. Some mean-reversion signals, but expect modest harvest and tighter cost discipline."
    elif score >= cfg.VERDICT_WEAK_MIN:
        verdict, color = "weak", "amber"
        headline = "Weak fit. The series shows limited mean reversion; results will depend heavily on regime stability."
    else:
        verdict, color = "unsuitable", "red"
        headline = "Unsuitable. The series does not behave as a mean-reverting process — Shannon's Demon will likely lose money on it."

    # Top reasons: pick the three components driving the verdict
    label_map = {
        "adf": "ADF stationarity",
        "kpss": "KPSS level-stationarity",
        "hurst": "Hurst exponent",
        "half_life": "AR(1) half-life",
        "regime_stability": "Regime stability",
        "vol_band": "Volatility regime",
    }
    if verdict in {"strong", "marginal"}:
        # Highlight the strongest contributors
        top = sorted(components.items(), key=lambda x: -x[1])[:3]
    else:
        # Highlight the weakest contributors
        top = sorted(components.items(), key=lambda x: x[1])[:3]
    top_reasons = [f"{label_map[k]}: score {v}/100" for k, v in top]

    red_flags: list[str] = []
    if adf.status == "fail":
        red_flags.append("ADF rejects mean reversion at any conventional level.")
    if kpss_r.status == "fail":
        red_flags.append("KPSS rejects level-stationarity — mean drifts.")
    if hurst.status == "fail":
        red_flags.append("Hurst > 0.55 — series trends rather than reverts.")
    if hl.status == "fail":
        red_flags.append("AR(1) coefficient is non-significant or has the wrong sign.")
    if regime.status == "fail":
        red_flags.append(f"{regime.n_shifts} regime shifts — structural breaks dominate.")
    if vol.status == "fail":
        red_flags.append("Volatility regime outside the sweet-spot band.")

    if hl.status == "pass":
        suggested = (
            f"Every {hl.suggested_rebalance_min_periods:.0f}–{hl.suggested_rebalance_max_periods:.0f} periods "
            f"(0.5×–1× half-life of {hl.half_life_human})."
        )
    else:
        suggested = "Half-life undefined — start with weekly rebalancing and tune based on backtest."

    # Max leverage rule of thumb: target Sortino ≥ 2 implies ~3x; otherwise scale linearly with score
    if score >= cfg.VERDICT_STRONG_MIN:
        max_lev = 3.0
    elif score >= cfg.VERDICT_MARGINAL_MIN:
        max_lev = 2.0
    elif score >= cfg.VERDICT_WEAK_MIN:
        max_lev = 1.5
    else:
        max_lev = 1.0

    return SuitabilityVerdict(
        score=score,
        verdict=verdict,
        color=color,
        headline=headline,
        top_reasons=top_reasons,
        red_flags=red_flags,
        suggested_rebalance=suggested,
        max_recommended_leverage=max_lev,
        component_scores=components,
    )
