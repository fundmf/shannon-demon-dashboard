"""Documentation tab content.

The text below is reproduced verbatim from the project brief. The image is
loaded from assets/efficient_frontier.png if present.
"""

from __future__ import annotations

import os

import streamlit as st


_DOC_PART_1 = """\
## Section 1: Shannon's Demon — The Rebalancing Paradox

Shannon's Demon is one of those beautiful ideas that feels like it shouldn't work but does. Claude Shannon (the information theory guy) described it in lectures at MIT in the 1960s as a thought experiment about how rebalancing can extract profit from pure volatility — even when the underlying asset goes nowhere.

### The Core Thought Experiment

Imagine a stock that does this every day:
- 50% chance it doubles (×2)
- 50% chance it halves (×0.5)

The geometric mean is √(2 × 0.5) = 1.0. Over time, the stock goes **nowhere**. Buy and hold = flat (actually slightly negative due to volatility drag).

Now split your money 50/50 between this stock and cash. Every period, rebalance back to 50/50.

**Start: $100 (50 stock, 50 cash)**

Stock doubles → 100 stock + 50 cash = $150. Rebalance → 75/75.
Stock halves → 37.50 stock + 75 cash = $112.50. Rebalance → 56.25/56.25.

You made money. From a stock that went nowhere. That's the demon.

The math: each full cycle (one up, one down) your wealth grows by a factor of 1.125. You're harvesting volatility.

### Why It Works

It's forced "buy low, sell high" mechanics. When the stock rips, you trim it (sell high). When it tanks, you top it up (buy low). Volatility, which is normally your enemy via variance drag, becomes your fuel.

The magic formula for the rebalancing bonus is approximately:

**Bonus ≈ ½ × w × (1-w) × σ²**

where w is your weight in the risky asset and σ² is its variance. More volatility = more harvest. The bonus peaks at w = 0.5.

### "Take on more risk but less risk at the same time"

This is the punchline that sounds contradictory. Here's the resolution:

**"More risk"** — You're now holding a highly volatile asset you might otherwise avoid. Individually, crypto/leveraged ETFs/meme coins look terrifying.

**"Less risk"** — At the *portfolio* level, mixing high-vol assets with cash (or uncorrelated assets) and rebalancing gives you:
- Lower portfolio volatility than the risky asset alone
- Bounded drawdowns (a 90% drop in the risky sleeve is only a ~45% hit if you're 50/50)
- Positive expected compounding from the volatility harvest

So you actively *seek out* volatile garbage — the more whipsaw, the better — because the rebalancing mechanism converts that chaos into return, while the cash sleeve caps your downside. You want the asset to be a mean-reverting volatility monster, not a trending winner.

### Practical Applications in Trading

**1. Crypto rebalancing portfolios.** Basket of 5–10 volatile alts at equal weights, rebalanced weekly/monthly. The noise between them is enormous and largely uncorrelated on short horizons — this is nearly ideal demon fuel. The catch: you need assets that don't go to zero. Survivorship matters more than anything.

**2. Risk parity / diversified rebalancing.** Bridgewater's All Weather is essentially Shannon's Demon dressed up. Stocks, bonds, gold, commodities — rebalance to equal risk contribution. The harvest comes from the uncorrelated noise.

**3. Leveraged/inverse ETF pairs.** Some traders rebalance between TQQQ and cash, or even long/short pairs. Works in chop, destroys you in trends.

**4. Barbell strategies.** Taleb-style: 90% T-bills, 10% in something explosive. Rebalance. You've capped downside at 10% while keeping asymmetric upside.

### The Catches (This Is Where People Blow Up)

The demon has teeth. It only works under specific conditions:

**Mean reversion is assumed.** If your volatile asset trends — up or down persistently — rebalancing *hurts*. You sell winners too early in bull markets and catch falling knives into zero.

**Costs eat the bonus fast.** The σ²/8 bonus is small in absolute terms. For a typical stock at 20% annual vol, it's ~0.5%/year. You need either serious volatility (crypto-level) or near-zero transaction costs.

**Correlation kills it.** Two assets that move together give you no harvest. The juice is in the cross-sectional noise.

**Survivorship bias.** Demon-style crypto portfolios from 2021 that included LUNA rebalanced straight into oblivion. One zero in the basket can wipe out years of harvest.

### A Mental Model

Shannon's Demon isn't a strategy so much as a *lens*. It reframes volatility from "risk to be minimized" to "raw material to be harvested" — but only when you have a mechanism (rebalancing), a structure (uncorrelated or mean-reverting components), and a cost profile (cheap execution, no funding bleed) that lets you actually extract it.

For a practical build: equal-weight basket of 5–8 liquid, uncorrelated assets, monthly rebalance, no leverage, sized so that a single asset going to zero costs you ≤15% of the portfolio. That's the demon in its natural habitat.
"""


_DOC_PART_2_INTRO = """\
## Section 2: Leveraging for Relatively Lower Risk (Capital Market Line)
"""

_DOC_PART_2_BODY = """\
The diagram is a classic **Capital Market Line** chart. Translation of each letter:

- **Curve (orange):** The efficient frontier — the best risk/return portfolios you can build from a set of assets.
- **R:** The risk-free rate (cash/T-bills).
- **A:** The "tangency portfolio" — the best-bang-for-buck portfolio on the curve. Highest return *per unit of risk*.
- **B:** A riskier portfolio further along the curve. Higher return, but you took on lots of risk to get it.
- **C:** Here's the magic. Same risk as B, but **higher return**. How? You held portfolio A (the efficient one) and **leveraged it up** using borrowed money.
- **D and E:** Even more leverage, or cheaper borrowing (R drops to R₁), pushes you further up the green line.

**The lesson of the diagram:** Don't pick a risky portfolio. Pick the *best* portfolio and apply leverage to it. You get the same risk level with more return.

**Simple summary:** Leverage a smart portfolio instead of building a dumb aggressive one.
"""


_DOC_PART_3 = """\
## Section 3: Tying It Together — Why the Demon + Leverage Stack Works

You build a Shannon's Demon engine on a mean-reverting asset — a stable, grinding, volatility-harvesting machine. Call this your **base portfolio**. It has low drawdowns (cash buffer), positive expected return from rebalancing, and a smooth equity curve (high Sortino ratio).

Then, because your base is so stable, you can safely **apply leverage on top of it**. The portfolio is now "riskier" in nominal terms (you're borrowing) but the underlying engine is so well-behaved that your actual blow-up risk stays low.

**Example in simple numbers:**
- Demon portfolio returns 8%/year, max drawdown 5%
- Lever it 3x → 24%/year return, max drawdown ~15%
- Compare to just buying a volatile stock: 24%/year expected, but 60% drawdowns

Same return, one-quarter the pain. That's point C on the diagram.
"""


_DOC_PART_4 = """\
## Section 4: The Sortino Connection

**Sortino ratio** = return divided by *downside* volatility only. It ignores upside wiggles (who cares if you're up?) and focuses on how much your portfolio hurts on the way down. A high Sortino ratio means your strategy rarely has big drops.

**Why this matters for leverage:** Leverage amplifies everything — including drawdowns. If you lever a strategy with a 20% drawdown 3x, you get a 60% drawdown and probably a margin call. But if your Sortino is high because drawdowns are tiny (say 3%), levering 3x only gives you 9%. Survivable.

**Tight stop-losses + high Sortino + Shannon's Demon base:**
1. Demon base = steady compounding, low vol
2. High Sortino = when you do lose, it's small
3. Tight SL on the leveraged sleeve = caps your downside per trade
4. You can now run meaningful leverage because each failure mode is bounded

**Simple summary:** High Sortino earns you the right to use leverage. Tight stops keep you alive while you use it.
"""


def render_documentation_tab() -> None:
    """Render the educational reference material."""
    st.title("Documentation")
    st.caption(
        "Reference material on Shannon's Demon, leverage, and the Sortino ratio. "
        "Read this before drawing conclusions from the analysis tab."
    )

    st.markdown(_DOC_PART_1)

    st.markdown(_DOC_PART_2_INTRO)
    img_path = os.path.join("assets", "efficient_frontier.png")
    if os.path.exists(img_path):
        st.image(img_path, caption="Capital Market Line", use_container_width=True)
    else:
        st.info(
            "Drop your efficient frontier diagram at `assets/efficient_frontier.png` "
            "to display it here."
        )
    st.markdown(_DOC_PART_2_BODY)

    st.markdown(_DOC_PART_3)
    st.markdown(_DOC_PART_4)


# ---------------------------------------------------------------------------
# Assumptions & Limitations tab
# ---------------------------------------------------------------------------

# Each entry: (formal statement, plain-English version)
_ASSUMPTIONS_MODELLING: list[tuple[str, str]] = [
    (
        "Monte Carlo Sleeve B assumes stationary distributional parameters.",
        "Plain English: We assume your crypto strategy keeps performing the same way "
        "in the future as the numbers you typed in. Real strategies have good years and "
        "bad years — the win rate and volatility from 2023 are not the win rate and "
        "volatility from 2026. Treat the Sleeve B inputs as 'best-case averages' and try "
        "stressing them downward to see how fragile the result is.",
    ),
    (
        "Sleeve B returns are drawn from a Student-t distribution with df=4.",
        "Plain English: We use a fat-tailed bell curve to simulate crypto returns instead "
        "of a normal one, because crypto really does have more big moves than a normal "
        "distribution would suggest. df=4 is a sensible default but real markets sometimes "
        "have even fatter tails (think LUNA, FTX). The simulator will under-state the "
        "frequency of catastrophic days.",
    ),
    (
        "Win rate is informational; realised distribution is set by mean + vol.",
        "Plain English: The 'win rate' slider is mostly there for reference — what really "
        "drives the simulation is the expected return and volatility you set. If your "
        "real strategy has a 70% win rate but tiny wins and huge losses, the simulator "
        "won't capture that asymmetry exactly. Use the stop-loss input to bound it.",
    ),
    (
        "Sleeve A is generated by stationary block bootstrap of the historical demon "
        "equity curve (mean block length ≈ 20).",
        "Plain English: For Sleeve A we replay short chunks of your real history in random "
        "order to create plausible alternative futures. This preserves the day-to-day "
        "wiggle of your asset but loses any very long-memory pattern (like 'crypto runs "
        "for 6 months then crashes for 6 months'). If your asset has long cycles, the "
        "bootstrap will under-represent them.",
    ),
    (
        "Correlation between sleeves is enforced via a Gaussian copula on standardised "
        "innovations.",
        "Plain English: The correlation slider works on day-to-day moves, but it doesn't "
        "guarantee that both sleeves crash together in a real crisis. In 2008 and 2020, "
        "everything correlated to 1.0 on the worst days — Gaussian copulas don't capture "
        "that 'tail dependence'. Set correlation higher than you'd expect normally if you "
        "want a realistic crisis stress test.",
    ),
    (
        "Sleeve A and Sleeve B are continuously re-weighted to the target allocation each "
        "period (no allocation drift).",
        "Plain English: The simulator assumes you continuously top up the smaller sleeve "
        "and trim the larger one to keep your allocation exactly on target. In real life "
        "you'd rebalance the two sleeves periodically (monthly or quarterly), which means "
        "the real combined return will differ slightly from the simulated one — usually "
        "by a small amount.",
    ),
    (
        "Risk-free rate is constant across the whole simulation horizon.",
        "Plain English: The model uses one risk-free rate the whole way through (default "
        "4%). In reality central banks change rates and your borrow cost changes with "
        "them. If you're modelling a multi-year scenario, the Sharpe and Sortino numbers "
        "are best treated as 'as of today's rate environment'.",
    ),
]


_ASSUMPTIONS_STATISTICAL: list[tuple[str, str]] = [
    (
        "Half-life estimates are point estimates with wide confidence intervals on short "
        "samples.",
        "Plain English: The 'half-life' number tells you how fast the price snaps back to "
        "its mean — but if you only have ~250 rows, that number could easily be 50% off "
        "in either direction. Don't tune your rebalance frequency to the exact half-life. "
        "Treat the suggested range (0.5×–1× half-life) as a starting point, not a precise "
        "answer.",
    ),
    (
        "Hurst exponent is noisy — both R/S and variance methods are sensitive to sample "
        "size and outliers.",
        "Plain English: The Hurst exponent is supposed to tell you 'is this thing trending "
        "or mean-reverting?' but it's a famously unstable number. We compute it two "
        "different ways and flag when they disagree by more than 0.10. If they disagree, "
        "don't trust either one — look at the half-life and ADF instead.",
    ),
    (
        "ADF and KPSS p-values are interpreted at conventional thresholds (5%/10%) without "
        "a multiple-comparisons correction.",
        "Plain English: We treat 'p < 0.05' as a pass for ADF and 'p > 0.05' as a pass for "
        "KPSS. These are the textbook thresholds. We're not adjusting for the fact that "
        "you're running multiple tests on the same data — if you slice your data many "
        "ways, eventually one will pass by luck.",
    ),
    (
        "KPSS critical-value table is interpolated outside its tabulated range.",
        "Plain English: The KPSS test only has exact answers at a few p-value points "
        "(0.01, 0.05, 0.10). When your real p-value is between those, statsmodels has "
        "to estimate it. We flag this as a 'boundary warning' but the test still works "
        "fine — just don't read too much into the exact decimal.",
    ),
    (
        "Regime detection (heuristic) flags points where the rolling mean moves > 2σ from "
        "its prior window — it does not estimate change-point uncertainty.",
        "Plain English: The 'regime shift' markers are an early-warning, not a precise "
        "scientific result. They tell you 'the average price moved a lot here' — but "
        "they can be triggered by a single big day, and they don't tell you how confident "
        "we are in each shift. PELT (the optional method) is more rigorous but heavier.",
    ),
    (
        "Annualised volatility uses log returns and assumes the sampling interval is "
        "uniform.",
        "Plain English: Volatility numbers assume your data points are evenly spaced. "
        "If your CSV has gaps (weekends, holidays, exchange downtime), the volatility "
        "estimate will be a little off. We warn you when we detect big gaps.",
    ),
    (
        "Shannon harvest formula is the continuous-time GBM approximation.",
        "Plain English: The bonus formula `½·w·(1-w)·σ²` is from a textbook ideal "
        "world: continuous trading, no costs, perfectly random returns. Your real harvest "
        "depends on how often you actually rebalance, your transaction costs, and "
        "whether the asset really mean-reverts. Use the formula as a ceiling, not a "
        "forecast.",
    ),
]


_ASSUMPTIONS_COSTS_LEVERAGE: list[tuple[str, str]] = [
    (
        "Transaction cost model is linear in turnover (bps × notional).",
        "Plain English: We charge a flat number of basis points on every dollar moved at "
        "rebalance. Real costs include the bid-ask spread, slippage when your order is "
        "big, and exchange/broker fees that aren't proportional to size. If you trade in "
        "size, your real costs can be 2–5× the simple bps figure.",
    ),
    (
        "Leverage sensitivity assumes borrow cost = risk-free rate.",
        "Plain English: The leverage section assumes you can borrow at the risk-free rate "
        "(default 4%). In reality your prime broker, exchange, or DeFi protocol will "
        "charge you more — sometimes a lot more (10–20% on crypto, more in stress). "
        "If you want to model this realistically, set the Sleeve B funding cost slider "
        "and don't lever the whole portfolio above what your real broker would allow.",
    ),
    (
        "Funding cost on Sleeve B is paid every period regardless of position.",
        "Plain English: We charge funding on the leveraged portion every single period, "
        "including periods when you'd be flat in real life. This biases the result very "
        "slightly downward — fine for stress-testing.",
    ),
    (
        "Stop-loss is applied as a hard floor on each-period return × leverage.",
        "Plain English: We clip any single-period loss at the stop-loss percentage. Real "
        "stop-losses can slip during volatile moves — your fill price isn't always your "
        "stop price. The simulation is mildly optimistic on this.",
    ),
    (
        "Cash yield in Sleeve A is paid continuously without tax or compounding gaps.",
        "Plain English: The cash leg earns its yield smoothly every period. In real life "
        "you'd be in T-bills with discrete coupons, or in a money-market fund with daily "
        "interest accrual. Difference is small but exists.",
    ),
]


_ASSUMPTIONS_DATA_SCOPE: list[tuple[str, str]] = [
    (
        "The dashboard requires a `close` column; other OHLCV columns are optional.",
        "Plain English: As long as your CSV has a column called `close`, it'll work. "
        "Indicator columns (Bollinger bands, RSI, etc.) are ignored. Time stamps are "
        "preferred but if missing we use row index.",
    ),
    (
        "Duplicate timestamps are deduplicated by keeping the last row.",
        "Plain English: If your CSV has two rows with the same timestamp, we keep the "
        "later one. This is usually correct for late-arriving data revisions but could "
        "matter if your platform exports duplicates differently.",
    ),
    (
        "Below 250 observations: warning. Below 50: hard block.",
        "Plain English: Statistical tests need data to work. Under 250 rows the answers "
        "get unreliable, under 50 they're useless. Get more data or shorten your bar "
        "interval.",
    ),
    (
        "Sleeve B has no historical data — it is purely parametric.",
        "Plain English: We don't run an actual crypto strategy backtest because we don't "
        "have the data. Sleeve B is entirely 'if you tell us this strategy returns 40% "
        "with 80% vol, here's what that looks like'. The output is only as good as your "
        "inputs — be honest about your strategy's real numbers.",
    ),
    (
        "The allocation optimiser sweep uses ¼ of the main Monte Carlo iteration count "
        "for responsiveness.",
        "Plain English: When you click 'Find optimal allocation', we run a slimmer "
        "simulation at 21 different allocation levels (0%, 5%, ... 100%) so the result "
        "is fast. The optimum it finds is approximate, not exact. Re-run with more "
        "iterations in the sidebar if you want a sharper answer.",
    ),
]


_ASSUMPTIONS_OPERATIONAL: list[tuple[str, str]] = [
    (
        "Caching is keyed on a price-series hash + parameters; identical re-runs are "
        "instant but parameter changes invalidate the cache.",
        "Plain English: Move a slider and the simulation re-runs from scratch. Move it "
        "back and the result comes from cache instantly. If you change your CSV or any "
        "parameter, expect a fresh compute on the next view.",
    ),
    (
        "Cloudflare Tunnel exposes localhost:8501 — anyone with the URL can reach the "
        "dashboard unless Cloudflare Access is enabled.",
        "Plain English: The tunnel makes your app reachable on the public internet. By "
        "default there's no password. Step 8 of the README ('Protect with Cloudflare "
        "Access') adds email login — do this if the dashboard is on a public domain.",
    ),
    (
        "All compute runs in the user's browser session via Streamlit — no persistence.",
        "Plain English: Refresh the page and your results are gone (you'd need to "
        "re-upload). This is by design — no data leaves your machine, nothing is stored "
        "on disk. If you want to save results, screenshot or export the metric tables.",
    ),
]


def _render_assumption_block(title: str, items: list[tuple[str, str]]) -> None:
    """Render one accordion of (formal, plain-English) pairs."""
    st.subheader(title)
    for formal, plain in items:
        with st.expander(formal):
            st.markdown(plain)


def render_assumptions_tab() -> None:
    """Render the assumptions & limitations reference."""
    st.title("Assumptions & Limitations")
    st.caption(
        "Every model is wrong; some are useful. This page lists every assumption baked "
        "into the dashboard, in formal terms with a plain-English translation. Read this "
        "before allocating real capital based on the output."
    )

    st.error(
        "**This is not financial advice.** Past performance and simulated performance "
        "do not predict future results. Stress every assumption before allocating real "
        "capital."
    )

    _render_assumption_block(
        "1. Modelling assumptions (the Monte Carlo)", _ASSUMPTIONS_MODELLING,
    )
    _render_assumption_block(
        "2. Statistical-test assumptions (ADF / KPSS / Hurst / half-life / regime / vol)",
        _ASSUMPTIONS_STATISTICAL,
    )
    _render_assumption_block(
        "3. Costs, funding, leverage", _ASSUMPTIONS_COSTS_LEVERAGE,
    )
    _render_assumption_block(
        "4. Data and scope", _ASSUMPTIONS_DATA_SCOPE,
    )
    _render_assumption_block(
        "5. Operational / runtime", _ASSUMPTIONS_OPERATIONAL,
    )

    st.divider()
    st.markdown(
        "### How to stress-test these assumptions in the dashboard\n\n"
        "- **Sleeve B inputs are your best-case guess** → halve the expected return, "
        "double the vol, double the funding cost. If the combined Sortino is still > 1, "
        "you have margin of safety.\n"
        "- **Correlation in a crisis** → set the correlation slider to +0.7 or +0.8 and "
        "watch the worst-case drawdown bands.\n"
        "- **Transaction costs** → bump bps from 5 → 25. If the demon CAGR turns "
        "negative, your edge is too thin.\n"
        "- **Leverage** → use the leverage sensitivity slider. If the line goes red "
        "(>30% DD) before you reach your intended leverage, you can't actually run that "
        "leverage live."
    )
