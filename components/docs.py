"""Documentation tab content.

Educational reference material with the same colour-coded keyword system
used in the Analysis tab. Spans are inlined into the markdown strings —
keep them strategic (2-4 highlights per paragraph) so the page reads as
prose, not a Christmas tree.
"""

from __future__ import annotations

import os
import re

import streamlit as st


# ---------------------------------------------------------------------------
# Search helper — highlight matches without breaking inline HTML
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r"(<[^>]+>)")


def _apply_search(text: str, query: str) -> tuple[str, int]:
    """Wrap any case-insensitive matches of `query` in <mark class="search-hit">.

    Crucially, only matches that fall outside HTML tags are highlighted —
    so a search for 'span' does not bleed into the inline keyword spans
    used by the highlight system.

    Returns the (possibly modified) text and the number of matches.
    """
    if not query or not query.strip():
        return text, 0
    q = query.strip()
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    parts = _HTML_TAG_RE.split(text)
    n_matches = 0

    def _sub(m: re.Match) -> str:
        nonlocal n_matches
        n_matches += 1
        return f'<mark class="search-hit">{m.group()}</mark>'

    out = []
    for p in parts:
        if p.startswith("<") and p.endswith(">"):
            out.append(p)            # leave HTML tags untouched
        else:
            out.append(pattern.sub(_sub, p))
    return "".join(out), n_matches


def _section_contains(content_blocks: list[str], query: str) -> int:
    """Count case-insensitive matches in a list of plain-text blocks."""
    if not query or not query.strip():
        return 0
    pattern = re.compile(re.escape(query.strip()), re.IGNORECASE)
    n = 0
    for block in content_blocks:
        # strip HTML for counting purposes so attribute names don't count
        plain = _HTML_TAG_RE.sub("", block)
        n += len(pattern.findall(plain))
    return n


# ---------------------------------------------------------------------------
# Keyword legend — must match the one in app.py
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
# Documentation parts
# ---------------------------------------------------------------------------
_DOC_PART_1 = """\
## Shannon's Demon — The Rebalancing Paradox

<span class="kw-concept">Shannon's Demon</span> is one of those beautiful ideas that feels like it shouldn't work but does. Claude Shannon (the information theory guy) described it in lectures at MIT in the 1960s as a thought experiment about how <span class="kw-concept">rebalancing</span> can <span class="kw-good">extract profit from pure volatility</span> — even when the underlying asset goes nowhere.

### The Core Thought Experiment

Imagine a stock that does this every day:
- <span class="kw-num">50%</span> chance it doubles (<span class="kw-num">×2</span>)
- <span class="kw-num">50%</span> chance it halves (<span class="kw-num">×0.5</span>)

The <span class="kw-test">geometric mean</span> is <span class="kw-num">√(2 × 0.5) = 1.0</span>. Over time, the stock goes **nowhere**. Buy and hold = flat (actually slightly negative due to <span class="kw-warn">volatility drag</span>).

Now split your money <span class="kw-num">50/50</span> between this stock and cash. Every period, <span class="kw-concept">rebalance</span> back to 50/50.

**Start: $100 (50 stock, 50 cash)**

Stock doubles → 100 stock + 50 cash = $150. Rebalance → 75/75.
Stock halves → 37.50 stock + 75 cash = $112.50. Rebalance → 56.25/56.25.

You <span class="kw-good">made money</span>. From a stock that went nowhere. That's the demon.

The math: each full cycle (one up, one down) your wealth grows by a factor of <span class="kw-num">1.125</span>. You're <span class="kw-good">harvesting volatility</span>.

### Why It Works

It's forced "buy low, sell high" mechanics. When the stock rips, you trim it (<span class="kw-good">sell high</span>). When it tanks, you top it up (<span class="kw-good">buy low</span>). Volatility, which is normally your enemy via <span class="kw-warn">variance drag</span>, becomes your <span class="kw-good">fuel</span>.

The magic formula for the rebalancing bonus is approximately:

**<span class="kw-test">Bonus ≈ ½ × w × (1-w) × σ²</span>**

where <span class="kw-num">w</span> is your weight in the risky asset and <span class="kw-num">σ²</span> is its variance. More volatility = more harvest. The bonus peaks at <span class="kw-num">w = 0.5</span>.

### "Take on more risk but less risk at the same time"

This is the punchline that sounds contradictory. Here's the resolution:

**"More risk"** — You're now holding a <span class="kw-warn">highly volatile asset</span> you might otherwise avoid. Individually, crypto/leveraged ETFs/meme coins look terrifying.

**"Less risk"** — At the *portfolio* level, mixing high-vol assets with cash (or uncorrelated assets) and rebalancing gives you:
- <span class="kw-good">Lower portfolio volatility</span> than the risky asset alone
- <span class="kw-good">Bounded drawdowns</span> (a <span class="kw-num">90%</span> drop in the risky sleeve is only a <span class="kw-num">~45%</span> hit if you're 50/50)
- Positive expected compounding from the <span class="kw-good">volatility harvest</span>

So you actively *seek out* volatile garbage — the more whipsaw, the better — because the rebalancing mechanism converts that <span class="kw-warn">chaos</span> into <span class="kw-good">return</span>, while the cash sleeve caps your downside. You want the asset to be a <span class="kw-good">mean-reverting volatility monster</span>, not a <span class="kw-bad">trending winner</span>.

### Practical Applications in Trading

**1. Crypto rebalancing portfolios.** Basket of <span class="kw-num">5–10</span> volatile alts at equal weights, <span class="kw-concept">rebalanced</span> weekly/monthly. The noise between them is enormous and largely uncorrelated on short horizons — this is nearly ideal demon fuel. <span class="kw-caveat">The catch: you need assets that don't go to zero. Survivorship matters more than anything.</span>

**2. Risk parity / diversified rebalancing.** Bridgewater's <span class="kw-concept">All Weather</span> is essentially Shannon's Demon dressed up. Stocks, bonds, gold, commodities — rebalance to equal risk contribution. The <span class="kw-good">harvest comes from the uncorrelated noise</span>.

**3. Leveraged/inverse ETF pairs.** Some traders rebalance between TQQQ and cash, or even long/short pairs. <span class="kw-good">Works in chop</span>, <span class="kw-bad">destroys you in trends</span>.

**4. Barbell strategies.** Taleb-style: <span class="kw-num">90%</span> T-bills, <span class="kw-num">10%</span> in something explosive. Rebalance. You've capped downside at <span class="kw-num">10%</span> while keeping <span class="kw-good">asymmetric upside</span>.

### The Catches (This Is Where People Blow Up)

The demon has teeth. <span class="kw-caveat">It only works under specific conditions:</span>

**<span class="kw-caveat">Mean reversion is assumed.</span>** If your volatile asset trends — up or down persistently — rebalancing *<span class="kw-bad">hurts</span>*. You sell winners too early in bull markets and <span class="kw-bad">catch falling knives</span> into zero.

**<span class="kw-caveat">Costs eat the bonus fast.</span>** The <span class="kw-num">σ²/8</span> bonus is small in absolute terms. For a typical stock at <span class="kw-num">20%</span> annual vol, it's <span class="kw-num">~0.5%/year</span>. You need either serious volatility (crypto-level) or near-zero transaction costs.

**<span class="kw-caveat">Correlation kills it.</span>** Two assets that move together give you <span class="kw-bad">no harvest</span>. The juice is in the cross-sectional noise.

**<span class="kw-caveat">Survivorship bias.</span>** Demon-style crypto portfolios from 2021 that included <span class="kw-bad">LUNA</span> rebalanced straight into <span class="kw-bad">oblivion</span>. One zero in the basket can wipe out years of harvest.

### A Mental Model

Shannon's Demon isn't a strategy so much as a *lens*. It reframes volatility from "<span class="kw-bad">risk to be minimized</span>" to "<span class="kw-good">raw material to be harvested</span>" — but only when you have a <span class="kw-concept">mechanism</span> (rebalancing), a <span class="kw-concept">structure</span> (uncorrelated or mean-reverting components), and a <span class="kw-concept">cost profile</span> (cheap execution, no funding bleed) that lets you actually extract it.

For a practical build: equal-weight basket of <span class="kw-num">5–8</span> liquid, uncorrelated assets, monthly rebalance, <span class="kw-good">no leverage</span>, sized so that a single asset going to zero costs you <span class="kw-num">≤15%</span> of the portfolio. That's the demon in its natural habitat.
"""


_DOC_PART_2_INTRO = """\
## Leveraging for Relatively Lower Risk (Capital Market Line)
"""

_DOC_PART_2_BODY = """\
The diagram is a classic **<span class="kw-concept">Capital Market Line</span>** chart. Translation of each letter:

- **Curve (orange):** The <span class="kw-concept">efficient frontier</span> — the best risk/return portfolios you can build from a set of assets.
- **R:** The <span class="kw-concept">risk-free rate</span> (cash/T-bills).
- **A:** The "<span class="kw-concept">tangency portfolio</span>" — the best-bang-for-buck portfolio on the curve. <span class="kw-good">Highest return *per unit of risk*</span>.
- **B:** A <span class="kw-warn">riskier portfolio</span> further along the curve. Higher return, but you took on lots of risk to get it.
- **C:** Here's the magic. Same risk as B, but **<span class="kw-good">higher return</span>**. How? You held portfolio A (the efficient one) and **<span class="kw-concept">leveraged it up</span>** using borrowed money.
- **D and E:** Even more leverage, or cheaper borrowing (R drops to R₁), pushes you further up the green line.

**The lesson of the diagram:** Don't pick a risky portfolio. Pick the *best* portfolio and apply <span class="kw-concept">leverage</span> to it. You get the <span class="kw-good">same risk level with more return</span>.

**Simple summary:** Leverage a smart portfolio instead of building a dumb aggressive one.
"""


_DOC_PART_3 = """\
## Tying It Together — Why the Demon + Leverage Stack Works

You build a <span class="kw-concept">Shannon's Demon engine</span> on a <span class="kw-good">mean-reverting asset</span> — a stable, grinding, volatility-harvesting machine. Call this your **<span class="kw-concept">base portfolio</span>**. It has <span class="kw-good">low drawdowns</span> (cash buffer), positive expected return from rebalancing, and a smooth equity curve (<span class="kw-good">high Sortino ratio</span>).

Then, because your base is so stable, you can safely **apply <span class="kw-concept">leverage</span> on top of it**. The portfolio is now "<span class="kw-warn">riskier</span>" in nominal terms (you're borrowing) but the underlying engine is so well-behaved that your <span class="kw-good">actual blow-up risk stays low</span>.

**Example in simple numbers:**
- Demon portfolio returns <span class="kw-num">8%/year</span>, max drawdown <span class="kw-num">5%</span>
- Lever it <span class="kw-num">3x</span> → <span class="kw-num">24%/year</span> return, max drawdown <span class="kw-num">~15%</span>
- Compare to just buying a volatile stock: <span class="kw-num">24%/year</span> expected, but <span class="kw-bad">60% drawdowns</span>

<span class="kw-good">Same return, one-quarter the pain.</span> That's point C on the diagram.
"""


_DOC_PART_4 = """\
## The Sortino Connection

**<span class="kw-test">Sortino ratio</span>** = return divided by *downside* volatility only. It ignores upside wiggles (who cares if you're up?) and focuses on how much your portfolio hurts on the way down. A <span class="kw-good">high Sortino ratio</span> means your strategy rarely has big drops.

**Why this matters for leverage:** Leverage amplifies everything — including drawdowns. If you lever a strategy with a <span class="kw-num">20%</span> drawdown <span class="kw-num">3x</span>, you get a <span class="kw-bad">60% drawdown</span> and probably a <span class="kw-bad">margin call</span>. But if your Sortino is high because drawdowns are tiny (say <span class="kw-num">3%</span>), levering <span class="kw-num">3x</span> only gives you <span class="kw-num">9%</span>. <span class="kw-good">Survivable</span>.

**Tight stop-losses + high Sortino + Shannon's Demon base:**
1. <span class="kw-concept">Demon base</span> = steady compounding, low vol
2. <span class="kw-good">High Sortino</span> = when you do lose, it's small
3. <span class="kw-good">Tight SL</span> on the leveraged sleeve = caps your downside per trade
4. You can now run <span class="kw-good">meaningful leverage</span> because each failure mode is bounded

**Simple summary:** High Sortino earns you the right to use leverage. Tight stops keep you alive while you use it.
"""


# ---------------------------------------------------------------------------
def _section_header(num: str, title_short: str) -> None:
    """Render the section number tag with a right-aligned short title."""
    st.markdown(
        f'<div class="doc-section-tag">'
        f'<span>SECTION {num}</span>'
        f'<span class="doc-section-tag-right">{title_short}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_documentation_tab() -> None:
    """Render the educational reference material with search + cards."""
    st.title("Documentation")
    st.caption(
        "Reference material on Shannon's Demon, leverage, and the Sortino ratio. "
        "Read this before drawing conclusions from the analysis tab."
    )
    st.markdown(KW_LEGEND_HTML, unsafe_allow_html=True)

    # ---- search bar -----------------------------------------------------
    search = st.text_input(
        "Search the documentation",
        key="docs_search",
        placeholder="e.g. 'half-life', 'Sortino', 'leverage', 'survivorship'",
        label_visibility="collapsed",
    )

    # Pre-count matches per section so we can show a summary
    sections = [
        ("01", "Rebalancing paradox", [_DOC_PART_1]),
        ("02", "Capital Market Line", [_DOC_PART_2_INTRO, _DOC_PART_2_BODY]),
        ("03", "Demon + Leverage stack", [_DOC_PART_3]),
        ("04", "Sortino connection", [_DOC_PART_4]),
    ]
    if search and search.strip():
        per_section = [(num, title, _section_contains(blocks, search))
                       for num, title, blocks in sections]
        total = sum(n for _, _, n in per_section)
        if total == 0:
            st.markdown(
                f'<div class="doc-search-info">No matches for '
                f'<strong>"{search}"</strong>.</div>',
                unsafe_allow_html=True,
            )
        else:
            breakdown = " · ".join(
                f"S{num} <strong>{n}</strong>" for num, _, n in per_section if n > 0
            )
            st.markdown(
                f'<div class="doc-search-info"><strong>{total}</strong> matches '
                f'for <strong>"{search}"</strong> &nbsp;·&nbsp; {breakdown}</div>',
                unsafe_allow_html=True,
            )

    # ---- Section 01 -----------------------------------------------------
    with st.container(border=True):
        _section_header("01", "Rebalancing paradox")
        body, _ = _apply_search(_DOC_PART_1, search)
        st.markdown(body, unsafe_allow_html=True)

    # ---- Section 02 (with image) ---------------------------------------
    with st.container(border=True):
        _section_header("02", "Capital Market Line")
        intro, _ = _apply_search(_DOC_PART_2_INTRO, search)
        st.markdown(intro, unsafe_allow_html=True)

        img_path = os.path.join("assets", "efficient_frontier.png")
        if os.path.exists(img_path):
            st.image(img_path, caption="Capital Market Line",
                     use_container_width=True)
        else:
            st.info(
                "Drop your efficient frontier diagram at "
                "`assets/efficient_frontier.png` to display it here."
            )

        body2, _ = _apply_search(_DOC_PART_2_BODY, search)
        st.markdown(body2, unsafe_allow_html=True)

    # ---- Section 03 -----------------------------------------------------
    with st.container(border=True):
        _section_header("03", "Demon + Leverage stack")
        body, _ = _apply_search(_DOC_PART_3, search)
        st.markdown(body, unsafe_allow_html=True)

    # ---- Section 04 -----------------------------------------------------
    with st.container(border=True):
        _section_header("04", "Sortino connection")
        body, _ = _apply_search(_DOC_PART_4, search)
        st.markdown(body, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Assumptions & Limitations tab
# ---------------------------------------------------------------------------

# Each entry: (formal statement, plain-English version) — both already
# include keyword highlight spans inline.

_ASSUMPTIONS_MODELLING: list[tuple[str, str]] = [
    (
        '<span class="kw-test">Monte Carlo</span> Sleeve B assumes <span class="kw-caveat">stationary distributional parameters</span>.',
        'Plain English: We <span class="kw-caveat">assume your crypto strategy keeps performing the same way</span> '
        'in the future as the numbers you typed in. Real strategies have <span class="kw-good">good years</span> '
        'and <span class="kw-bad">bad years</span> — the <span class="kw-test">win rate</span> and '
        '<span class="kw-test">volatility</span> from 2023 are not the win rate and volatility from 2026. '
        'Treat the Sleeve B inputs as "<span class="kw-warn">best-case averages</span>" and try '
        'stressing them downward to see how <span class="kw-bad">fragile</span> the result is.',
    ),
    (
        '<span class="kw-concept">Sleeve B</span> returns are drawn from a <span class="kw-test">Student-t distribution</span> with <span class="kw-num">df=4</span>.',
        'Plain English: We use a <span class="kw-test">fat-tailed bell curve</span> to simulate crypto returns instead '
        'of a normal one, because crypto really does have more big moves than a normal '
        'distribution would suggest. <span class="kw-num">df=4</span> is a sensible default but real markets sometimes '
        'have <span class="kw-warn">even fatter tails</span> (think LUNA, FTX). The simulator will '
        '<span class="kw-caveat">under-state the frequency of catastrophic days</span>.',
    ),
    (
        '<span class="kw-test">Win rate</span> is informational; realised distribution is set by mean + vol.',
        'Plain English: The "<span class="kw-test">win rate</span>" slider is mostly there for reference — what really '
        'drives the simulation is the <span class="kw-test">expected return</span> and '
        '<span class="kw-test">volatility</span> you set. If your real strategy has a '
        '<span class="kw-num">70%</span> win rate but tiny wins and huge losses, the simulator '
        '<span class="kw-caveat">won\'t capture that asymmetry exactly</span>. Use the '
        '<span class="kw-concept">stop-loss</span> input to bound it.',
    ),
    (
        '<span class="kw-concept">Sleeve A</span> is generated by <span class="kw-test">stationary block bootstrap</span> of the historical demon equity curve (mean block length ≈ <span class="kw-num">20</span>).',
        'Plain English: For Sleeve A we <span class="kw-good">replay short chunks of your real history</span> in random '
        'order to create plausible alternative futures. This preserves the day-to-day '
        'wiggle of your asset but <span class="kw-caveat">loses any very long-memory pattern</span> '
        '(like "crypto runs for 6 months then crashes for 6 months"). If your asset has '
        '<span class="kw-warn">long cycles</span>, the bootstrap will under-represent them.',
    ),
    (
        'Correlation between sleeves is enforced via a <span class="kw-test">Gaussian copula</span> on standardised innovations.',
        'Plain English: The <span class="kw-test">correlation</span> slider works on day-to-day moves, but it '
        '<span class="kw-caveat">doesn\'t guarantee that both sleeves crash together in a real crisis</span>. '
        'In <span class="kw-num">2008</span> and <span class="kw-num">2020</span>, '
        '<span class="kw-bad">everything correlated to 1.0 on the worst days</span> — Gaussian copulas '
        'don\'t capture that "<span class="kw-bad">tail dependence</span>". Set correlation higher '
        'than you\'d expect normally if you want a realistic crisis stress test.',
    ),
    (
        'Sleeve A and Sleeve B are <span class="kw-caveat">continuously re-weighted</span> to the target allocation each period (no allocation drift).',
        'Plain English: The simulator assumes you continuously top up the smaller sleeve '
        'and trim the larger one to keep your allocation exactly on target. In real life '
        'you\'d rebalance the two sleeves <span class="kw-warn">periodically</span> (monthly or quarterly), which means '
        'the real combined return will <span class="kw-caveat">differ slightly from the simulated one</span> — usually '
        'by a small amount.',
    ),
    (
        '<span class="kw-test">Risk-free rate</span> is constant across the whole simulation horizon.',
        'Plain English: The model uses one risk-free rate the whole way through (default '
        '<span class="kw-num">4%</span>). In reality central banks change rates and your '
        '<span class="kw-warn">borrow cost changes with them</span>. If you\'re modelling a multi-year '
        'scenario, the <span class="kw-test">Sharpe</span> and <span class="kw-test">Sortino</span> '
        'numbers are <span class="kw-caveat">best treated as "as of today\'s rate environment"</span>.',
    ),
]


_ASSUMPTIONS_STATISTICAL: list[tuple[str, str]] = [
    (
        '<span class="kw-test">Half-life</span> estimates are point estimates with <span class="kw-warn">wide confidence intervals</span> on short samples.',
        'Plain English: The "<span class="kw-test">half-life</span>" number tells you how fast the price snaps back to '
        'its mean — but if you only have <span class="kw-num">~250</span> rows, that number could '
        'easily be <span class="kw-warn">50% off in either direction</span>. Don\'t tune your rebalance frequency '
        'to the exact half-life. Treat the suggested range '
        '(<span class="kw-num">0.5×–1×</span> half-life) as a starting point, not a precise answer.',
    ),
    (
        '<span class="kw-test">Hurst exponent</span> is <span class="kw-warn">noisy</span> — both R/S and variance methods are sensitive to sample size and outliers.',
        'Plain English: The <span class="kw-test">Hurst exponent</span> is supposed to tell you "is this thing trending '
        'or mean-reverting?" but it\'s a <span class="kw-warn">famously unstable number</span>. We compute it two '
        'different ways and flag when they disagree by more than <span class="kw-num">0.10</span>. '
        'If they disagree, <span class="kw-caveat">don\'t trust either one</span> — look at the '
        '<span class="kw-test">half-life</span> and <span class="kw-test">ADF</span> instead.',
    ),
    (
        '<span class="kw-test">ADF</span> and <span class="kw-test">KPSS</span> p-values are interpreted at conventional thresholds (<span class="kw-num">5%/10%</span>) without a multiple-comparisons correction.',
        'Plain English: We treat "<span class="kw-num">p &lt; 0.05</span>" as a pass for ADF and '
        '"<span class="kw-num">p &gt; 0.05</span>" as a pass for KPSS. These are the textbook thresholds. '
        '<span class="kw-caveat">We\'re not adjusting for the fact that you\'re running multiple tests on the same data</span> — '
        'if you slice your data many ways, eventually one will pass <span class="kw-warn">by luck</span>.',
    ),
    (
        '<span class="kw-test">KPSS</span> critical-value table is <span class="kw-caveat">interpolated</span> outside its tabulated range.',
        'Plain English: The KPSS test only has exact answers at a few p-value points '
        '(<span class="kw-num">0.01, 0.05, 0.10</span>). When your real p-value is between those, '
        'statsmodels has to <span class="kw-warn">estimate it</span>. We flag this as a "boundary warning" '
        'but the test still works fine — just don\'t read too much into the exact decimal.',
    ),
    (
        '<span class="kw-test">Regime detection</span> (heuristic) flags points where the rolling mean moves &gt; <span class="kw-num">2σ</span> from its prior window — it does not estimate change-point uncertainty.',
        'Plain English: The "<span class="kw-warn">regime shift</span>" markers are an early-warning, not a precise '
        'scientific result. They tell you "the average price moved a lot here" — but '
        'they can be <span class="kw-warn">triggered by a single big day</span>, and they don\'t tell '
        'you how confident we are in each shift. <span class="kw-test">PELT</span> (the optional method) '
        'is more rigorous but heavier.',
    ),
    (
        '<span class="kw-test">Annualised volatility</span> uses log returns and assumes the sampling interval is uniform.',
        'Plain English: <span class="kw-test">Volatility</span> numbers <span class="kw-caveat">assume your data points are evenly spaced</span>. '
        'If your CSV has <span class="kw-warn">gaps</span> (weekends, holidays, exchange downtime), the volatility '
        'estimate will be a little off. We warn you when we detect big gaps.',
    ),
    (
        '<span class="kw-concept">Shannon harvest</span> formula is the continuous-time GBM approximation.',
        'Plain English: The bonus formula <span class="kw-test">½·w·(1-w)·σ²</span> is from a textbook ideal '
        'world: <span class="kw-caveat">continuous trading, no costs, perfectly random returns</span>. Your real harvest '
        'depends on how often you actually rebalance, your transaction costs, and '
        'whether the asset really mean-reverts. <span class="kw-warn">Use the formula as a ceiling, not a forecast</span>.',
    ),
]


_ASSUMPTIONS_COSTS_LEVERAGE: list[tuple[str, str]] = [
    (
        'Transaction cost model is <span class="kw-caveat">linear in turnover</span> (bps × notional).',
        'Plain English: We charge a flat number of basis points on every dollar moved at '
        'rebalance. Real costs include the <span class="kw-warn">bid-ask spread</span>, '
        '<span class="kw-warn">slippage</span> when your order is big, and exchange/broker fees that '
        '<span class="kw-caveat">aren\'t proportional to size</span>. If you trade in size, your real '
        'costs can be <span class="kw-bad">2–5×</span> the simple bps figure.',
    ),
    (
        '<span class="kw-concept">Leverage sensitivity</span> assumes <span class="kw-caveat">borrow cost = risk-free rate</span>.',
        'Plain English: The leverage section assumes you can borrow at the risk-free rate '
        '(default <span class="kw-num">4%</span>). In reality your prime broker, exchange, or DeFi protocol '
        'will <span class="kw-bad">charge you more</span> — sometimes a lot more '
        '(<span class="kw-num">10–20%</span> on crypto, more in stress). If you want to model this '
        'realistically, set the Sleeve B funding cost slider and don\'t lever the whole '
        'portfolio above what your real broker would allow.',
    ),
    (
        'Funding cost on Sleeve B is paid every period <span class="kw-caveat">regardless of position</span>.',
        'Plain English: We charge funding on the leveraged portion every single period, '
        '<span class="kw-warn">including periods when you\'d be flat in real life</span>. This biases the result '
        'very slightly downward — <span class="kw-good">fine for stress-testing</span>.',
    ),
    (
        '<span class="kw-concept">Stop-loss</span> is applied as a hard floor on each-period return × leverage.',
        'Plain English: We clip any single-period loss at the stop-loss percentage. Real '
        'stop-losses can <span class="kw-warn">slip during volatile moves</span> — your fill price '
        'isn\'t always your stop price. The simulation is <span class="kw-caveat">mildly optimistic on this</span>.',
    ),
    (
        'Cash yield in Sleeve A is paid <span class="kw-caveat">continuously without tax or compounding gaps</span>.',
        'Plain English: The cash leg earns its yield smoothly every period. In real life '
        'you\'d be in T-bills with discrete coupons, or in a money-market fund with daily '
        'interest accrual. <span class="kw-good">Difference is small but exists</span>.',
    ),
]


_ASSUMPTIONS_DATA_SCOPE: list[tuple[str, str]] = [
    (
        'The dashboard requires a <code>close</code> column; other OHLCV columns are optional.',
        'Plain English: As long as your CSV has a column called <code>close</code>, it\'ll work. '
        'Indicator columns (Bollinger bands, RSI, etc.) are <span class="kw-good">ignored</span>. Time stamps are '
        'preferred but if missing we use row index.',
    ),
    (
        'Duplicate timestamps are deduplicated by <span class="kw-caveat">keeping the last row</span>.',
        'Plain English: If your CSV has two rows with the same timestamp, we keep the '
        'later one. This is usually correct for late-arriving data revisions but '
        '<span class="kw-warn">could matter if your platform exports duplicates differently</span>.',
    ),
    (
        'Below <span class="kw-num">250</span> observations: warning. Below <span class="kw-num">50</span>: hard block.',
        'Plain English: Statistical tests need data to work. Under <span class="kw-num">250</span> rows the answers '
        'get <span class="kw-warn">unreliable</span>, under <span class="kw-num">50</span> they\'re '
        '<span class="kw-bad">useless</span>. Get more data or shorten your bar interval.',
    ),
    (
        '<span class="kw-concept">Sleeve B</span> has <span class="kw-caveat">no historical data</span> — it is purely parametric.',
        'Plain English: We <span class="kw-bad">don\'t run an actual crypto strategy backtest</span> because we don\'t '
        'have the data. Sleeve B is entirely "if you tell us this strategy returns '
        '<span class="kw-num">40%</span> with <span class="kw-num">80%</span> vol, here\'s what that '
        'looks like". <span class="kw-warn">The output is only as good as your inputs</span> — be honest '
        'about your strategy\'s real numbers.',
    ),
    (
        'The <span class="kw-concept">allocation optimiser</span> sweep uses <span class="kw-num">¼</span> of the main Monte Carlo iteration count for responsiveness.',
        'Plain English: When you click "Find optimal allocation", we run a slimmer '
        'simulation at <span class="kw-num">21</span> different allocation levels (0%, 5%, ... 100%) '
        'so the result is fast. <span class="kw-caveat">The optimum it finds is approximate, not exact.</span> '
        'Re-run with more iterations in the sidebar if you want a sharper answer.',
    ),
]


_ASSUMPTIONS_OPERATIONAL: list[tuple[str, str]] = [
    (
        'Caching is keyed on a price-series hash + parameters; identical re-runs are instant but parameter changes invalidate the cache.',
        'Plain English: Move a slider and the simulation re-runs from scratch. Move it '
        'back and the result comes from cache <span class="kw-good">instantly</span>. If you change your CSV or any '
        'parameter, expect a fresh compute on the next view.',
    ),
    (
        '<span class="kw-concept">Cloudflare Tunnel</span> exposes localhost:8501 — anyone with the URL can reach the dashboard unless <span class="kw-good">Cloudflare Access</span> is enabled.',
        'Plain English: The tunnel makes your app reachable on the public internet. By '
        'default <span class="kw-bad">there\'s no password</span>. Step 8 of the README ("Protect with Cloudflare '
        'Access") adds email login — <span class="kw-good">do this if the dashboard is on a public domain</span>.',
    ),
    (
        'All compute runs in the user\'s browser session via Streamlit — <span class="kw-caveat">no persistence</span>.',
        'Plain English: Refresh the page and your results are gone (you\'d need to '
        're-upload). This is by design — <span class="kw-good">no data leaves your machine</span>, nothing is stored '
        'on disk. If you want to save results, screenshot or export the metric tables.',
    ),
]


def _render_assumption_block(title: str, items: list[tuple[str, str]]) -> None:
    """Render one accordion of (formal, plain-English) pairs."""
    st.subheader(title)
    for formal, plain in items:
        # Streamlit expanders don't render HTML in their label, so the
        # formal statement label stays plain — open the expander to see
        # the full highlighted text repeated as a heading + the
        # plain-English explanation underneath.
        plain_label = _strip_html(formal)
        with st.expander(plain_label):
            st.markdown(f"**{formal}**", unsafe_allow_html=True)
            st.markdown(plain, unsafe_allow_html=True)


def _strip_html(text: str) -> str:
    """Quick-and-dirty HTML tag stripper for use in expander labels."""
    import re
    return re.sub(r"<[^>]+>", "", text).replace("&lt;", "<").replace("&gt;", ">")


def render_assumptions_tab() -> None:
    """Render the assumptions & limitations reference."""
    st.title("Assumptions & Limitations")
    st.caption(
        "Every model is wrong; some are useful. This page lists every assumption baked "
        "into the dashboard, in formal terms with a plain-English translation. Read this "
        "before allocating real capital based on the output."
    )
    st.markdown(KW_LEGEND_HTML, unsafe_allow_html=True)

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
        '### How to stress-test these assumptions in the dashboard\n\n'
        '- **<span class="kw-concept">Sleeve B</span> inputs are your best-case guess** → halve the '
        'expected return, double the vol, double the funding cost. If the combined '
        '<span class="kw-test">Sortino</span> is still <span class="kw-num">&gt; 1</span>, '
        'you have <span class="kw-good">margin of safety</span>.\n'
        '- **<span class="kw-warn">Correlation in a crisis</span>** → set the correlation slider to '
        '<span class="kw-num">+0.7</span> or <span class="kw-num">+0.8</span> and watch the '
        '<span class="kw-bad">worst-case drawdown bands</span>.\n'
        '- **<span class="kw-test">Transaction costs</span>** → bump bps from '
        '<span class="kw-num">5</span> → <span class="kw-num">25</span>. If the demon CAGR turns '
        '<span class="kw-bad">negative</span>, your <span class="kw-bad">edge is too thin</span>.\n'
        '- **<span class="kw-concept">Leverage</span>** → use the leverage sensitivity slider. '
        'If the line goes <span class="kw-bad">red</span> '
        '(<span class="kw-num">&gt;30%</span> DD) before you reach your intended leverage, '
        'you <span class="kw-bad">can\'t actually run that leverage live</span>.',
        unsafe_allow_html=True,
    )
