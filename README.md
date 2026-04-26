# Shannon's Demon Dashboard

A production-grade Streamlit dashboard for assessing whether a price series is suitable for a Shannon's Demon (mean-reversion rebalancing) strategy, simulating a dual-sleeve portfolio that pairs the Demon with a crypto leverage sleeve, and stress-testing every parameter that matters: allocation, expected returns, leverage, costs, and regime assumptions.

---

## Part 1 — What this app does

Drop in any OHLCV-style CSV (TradingView exports work out of the box). The app cleans the data, runs a full statistical battery on the close series — ADF, KPSS, Hurst, half-life, regime detection, volatility — and produces a 0-100 suitability score with a plain-English verdict. It then runs a Monte Carlo simulation of a two-sleeve portfolio combining a Shannon's Demon allocation on the uploaded asset with a parametric crypto leverage sleeve, and lets you tune every input live: rebalancing rule, transaction costs, leverage, correlation, win rate, stop-loss. There's a documentation tab explaining the theory in plain English. Every parameter is exposed; nothing is hard-coded.

---

## Part 2 — Run it locally

1. Clone the repo from GitHub:
   ```
   git clone https://github.com/<your-username>/shannon-demon-dashboard.git
   cd shannon-demon-dashboard
   ```

2. Create a Python virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate    # macOS/Linux
   venv\Scripts\activate       # Windows
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the app:
   ```
   streamlit run app.py
   ```

5. Open `http://localhost:8501` in your browser. Drag in your CSV.

The first run downloads ~200 MB of dependencies (pandas, statsmodels, scipy, plotly). After that, startup is sub-5-second.

---

## Part 3 — Push your project to GitHub (first time)

Skip this section if you already have the repo on GitHub.

1. Go to [github.com/new](https://github.com/new). Name the repo `shannon-demon-dashboard`. Make it private if you want. **Do not** tick "Add a README" — your local one will be the one that lives in the repo.

2. From your project directory:
   ```
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/shannon-demon-dashboard.git
   git push -u origin main
   ```

3. Confirm the contents of your `.gitignore`:
   ```
   venv/
   __pycache__/
   .DS_Store
   .env
   .streamlit/secrets.toml
   cloudflared/*.json
   cert.pem
   ```
   These keep your virtualenv, OS junk files, secrets, and Cloudflare credentials out of GitHub.

If you accidentally pushed credentials, **rotate them immediately** — `git rm`-ing later doesn't remove them from history.

---

## Part 4 — Expose your local app to the internet with Cloudflare Tunnel

A Cloudflare Tunnel lets you serve your app from your own machine (or a VPS) to a public HTTPS URL on your own domain, without opening ports or configuring a firewall. It's free, secure, and takes about 10 minutes.

### Step 1: Install `cloudflared` on your machine

- **macOS (Homebrew):**
  ```
  brew install cloudflared
  ```

- **Windows:** download the `.msi` installer from [https://github.com/cloudflare/cloudflared/releases/latest](https://github.com/cloudflare/cloudflared/releases/latest) and run it. The installer registers `cloudflared.exe` on your PATH.

- **Linux (Debian/Ubuntu):**
  ```
  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
  sudo dpkg -i cloudflared.deb
  ```

Verify the install:
```
cloudflared --version
```

### Step 2: Log in to Cloudflare from the command line

```
cloudflared tunnel login
```

This opens a browser window. Pick the domain you want to use (e.g. `yourdomain.com`). Cloudflare saves a certificate to `~/.cloudflared/cert.pem` (or `%USERPROFILE%\.cloudflared\cert.pem` on Windows). Don't commit this file.

If you don't have a domain yet: buy one cheap from Cloudflare Registrar, Namecheap, or Porkbun. Then add it to Cloudflare by clicking **"Add a site"** in the Cloudflare dashboard and following the nameserver instructions. The domain has to be on Cloudflare DNS for the tunnel to route to it.

### Step 3: Create a tunnel

```
cloudflared tunnel create shannon-demon
```

This prints a tunnel ID (a UUID) and writes a credentials JSON file to `~/.cloudflared/<tunnel-id>.json`. Note both — you'll need them in Step 4.

### Step 4: Create a config file at `~/.cloudflared/config.yml`

Use `cloudflared/config.example.yml` in this repo as a template:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /Users/<you>/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: demon.yourdomain.com
    service: http://localhost:8501
    originRequest:
      connectTimeout: 30s
      keepAliveTimeout: 90s
      keepAliveConnections: 100
  - service: http_status:404
```

Replace `<your-tunnel-id>`, the credentials path, and the hostname with your real values. On Windows, the credentials path is something like `C:\Users\<you>\.cloudflared\<tunnel-id>.json`.

### Step 5: Create a DNS record pointing at the tunnel

```
cloudflared tunnel route dns shannon-demon demon.yourdomain.com
```

This creates a CNAME record in your Cloudflare DNS automatically. Double-check by visiting the Cloudflare dashboard → your domain → DNS — you should see a new entry pointing to `<tunnel-id>.cfargotunnel.com`.

### Step 6: Run the tunnel

In one terminal, start Streamlit:
```
streamlit run app.py
```

In a second terminal, start the tunnel:
```
cloudflared tunnel run shannon-demon
```

Visit `https://demon.yourdomain.com`. Your dashboard is live on HTTPS with no port-forwarding, no firewall changes, and no static IP needed.

### Step 7 (recommended): Run the tunnel as a service

So it survives reboots:

- **macOS / Linux:**
  ```
  sudo cloudflared service install
  ```

- **Windows (admin terminal):**
  ```
  cloudflared.exe service install
  ```

The service reads from `~/.cloudflared/config.yml` (or `%USERPROFILE%\.cloudflared\config.yml` on Windows) so make sure your config is there before installing.

### Step 8 (optional): Protect the dashboard with Cloudflare Access

The simplest way to keep the dashboard private without building a password system:

1. Cloudflare dashboard → **Zero Trust** → **Access** → **Applications** → **Add an application** → **Self-hosted**.
2. Hostname: `demon.yourdomain.com`.
3. Add a policy: name it "me only", action **Allow**, include rule **Emails** → enter your email.
4. Save.

Now anyone hitting the URL has to enter their email, get a one-time PIN, and authenticate before the tunnel even connects to your Streamlit. Good enough for a personal analysis tool.

---

## Part 5 — Troubleshooting

**"I see a 502 Bad Gateway."**
Streamlit isn't running or it's running on a different port. Check the terminal where you ran `streamlit run app.py` — it should say `Local URL: http://localhost:8501`. Make sure your tunnel config points to the same port.

**"DNS not resolving — `demon.yourdomain.com` doesn't load."**
Wait 1–2 minutes for DNS propagation. Confirm in Cloudflare dashboard → DNS that the CNAME record exists and proxying is enabled (orange cloud).

**"Tunnel won't start — credentials error."**
Double-check the path in `config.yml` exactly matches the JSON file location. On Windows, use forward slashes or escaped backslashes in YAML.

**"Streamlit can't find my CSV."**
The uploader works in-browser; paths aren't needed. Just drag and drop the file onto the upload widget.

**"Monte Carlo is too slow."**
Reduce iterations in the sidebar (default 1,000 — try 500). The first run is uncached; subsequent runs with the same parameters are instant. Heavy combinations: 5,000+ sims × 50,000+ rows × allocation sweep.

**"`hurst` package can't install on Python 3.12."**
The R/S Hurst is implemented from scratch in `analysis/stats_tests.py` — the `hurst` package is included as a fallback only. Pin to Python 3.11 if `pip install` fails on it, or remove it from `requirements.txt`.

**"I want to move off my laptop."**
Spin up a $5/month VPS (Hetzner, DigitalOcean, Vultr). Repeat steps 1–3 (clone, venv, install) and 4–7 (cloudflared install + config) on the VPS. Your tunnel config stays the same; just move the credentials file across with `scp`.

---

## Part 6 — Project structure walkthrough

```
shannon-demon-dashboard/
├── app.py                       # Streamlit entry point. Wires tabs together.
├── requirements.txt             # Pinned dependencies.
├── config.py                    # All thresholds, defaults, scoring weights.
│
├── analysis/
│   ├── stats_tests.py           # ADF, KPSS, Hurst, half-life, regime, vol, harvest.
│   ├── backtest.py              # Demon rebalancing simulation (deterministic).
│   ├── portfolio.py             # Dual-sleeve Monte Carlo (bootstrap + parametric).
│   └── interpretations.py       # Plain-English summaries + 0-100 scoring.
│
├── components/
│   ├── upload.py                # CSV parser + Streamlit uploader widget.
│   ├── charts.py                # Plotly figure builders (pure functions).
│   ├── controls.py              # Sidebar + Sleeve A/B control widgets.
│   └── docs.py                  # Documentation tab content.
│
├── assets/
│   └── efficient_frontier.png   # Drop your CML diagram here.
│
├── cloudflared/
│   └── config.example.yml       # Tunnel config template.
│
├── .gitignore
└── README.md
```

Where to look when you want to:

- Tweak suitability scoring → `config.py` (`SCORE_WEIGHTS`) and `analysis/interpretations.py`.
- Add a new statistical test → `analysis/stats_tests.py`, then expose it from `analysis/__init__.py` and call it in `app.py`'s `_section_stationarity` (or build a new section).
- Change a default → `config.py`. No magic numbers live elsewhere.
- Tune charts → `components/charts.py`. All Plotly is here.

---

## Part 7 — How to extend

### Adding a new statistical test

1. Add a `@dataclass` in `analysis/stats_tests.py` for the result shape.
2. Implement a `run_<test>(close: pd.Series) -> <Result>` function. Wrap in `try/except`; return a result with `status="error"` on failure.
3. Add an interpreter in `analysis/interpretations.py`.
4. (Optional) Add a chart builder in `components/charts.py`.
5. Render it from `app.py` in whichever section makes sense.
6. Update `SCORE_WEIGHTS` in `config.py` if it should affect the verdict.

### Adding a new rebalance rule

1. In `analysis/backtest.py`, extend the `RebalanceRule` literal and add the branch in `run_demon_backtest`.
2. In `components/controls.py`, add the option to `render_sleeve_a` with whatever knobs it needs.
3. Pipe the new control through `app.py`'s `_section_dual_sleeve` and into the cached backtest call.

### Adding a new sleeve type (bond ladder, options overlay, etc.)

1. Add a new simulator function in `analysis/portfolio.py` (analogous to `_calibrate_sleeve_b_innovations`).
2. Extend `run_dual_sleeve_simulation` to accept a third sleeve and combine returns with allocation weights.
3. Add a control panel in `components/controls.py` and wire it through `app.py`. The metrics table and charts already accept any number of sleeves with minor changes.

---

## Part 8 — Known limitations and disclaimers

- **Monte Carlo Sleeve B assumes stationary distributional parameters.** Real crypto strategies have regime-dependent performance — the win rate and vol you saw in 2023 are not the same as 2026.

- **Transaction cost model is linear in turnover.** Real costs include slippage, spread, funding, and can be non-linear at size. Recommended: stress the bps input until results break, and treat the bps you used in production as the lower bound.

- **Half-life estimates are point estimates with wide confidence intervals on short samples.** A series with 250 observations can produce a half-life with ±50% standard error.

- **Hurst exponent is noisy.** Both R/S and variance methods are sensitive to sample size and outliers. The dashboard reports both and flags when they diverge by > 0.10.

- **Sleeve A bootstrap preserves only short-range autocorrelation** (block bootstrap, geometric block length). If your data has long-memory structure, the bootstrap will under-represent it.

- **Correlation between sleeves is enforced via a Gaussian copula on standardised innovations.** The marginals (fat-tailed Sleeve B, bootstrap-resampled Sleeve A) are preserved, but tail dependence may not be.

- **The leverage sensitivity section assumes** funding costs match the risk-free rate. If your prime broker charges more, recompute manually with the actual borrow rate.

- **The allocation optimiser uses a small-MC sweep** (¼ of the main MC iteration count) to keep it responsive. The optimum is approximate, not exact.

**This is not financial advice. Past performance and simulated performance do not predict future results. Stress every assumption before allocating real capital.**
