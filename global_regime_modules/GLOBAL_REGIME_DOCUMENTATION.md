# Global Regime Module — Comprehensive Documentation

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [The Four Market Regimes](#3-the-four-market-regimes)
4. [Module: `data_fetcher.py` — DataFetcher](#4-module-data_fetcherpy--datafetcher)
5. [Module: `regime_analyzer.py` — RegimeAnalyzer](#5-module-regime_analyzerpy--regimeanalyzer)
   - [Technical Indicators](#51-technical-indicators)
   - [Regime Classification Logic](#52-regime-classification-logic)
   - [Exit Signal Logic](#53-exit-signal-logic)
   - [Backtesting & Performance](#54-backtesting--performance)
   - [Asset Allocation Recommendations](#55-asset-allocation-recommendations)
6. [Module: `global_regime_api/api.py` — FastAPI REST API](#6-module-global_regime_apiapipy--fastapi-rest-api)
7. [Module: `pages/global_regime.py` — Streamlit Dashboard](#7-module-pagesglobal_regimepy--streamlit-dashboard)
8. [Data Flow](#8-data-flow)
9. [Usage Examples](#9-usage-examples)
10. [Configuration Reference](#10-configuration-reference)

---

## 1. Overview

The **Global Regime Module** is the core analytical engine of iWealthBuilder. It continuously monitors the relative performance of two key macro assets — **Gold (GC=F)** and **the Indian equity benchmark Nifty 50 (^NSEI)** — and classifies the current market environment into one of four distinct **regimes**. Each regime maps directly to a recommended portfolio allocation, enabling rule-based, emotion-free asset rotation.

### Goals

| Goal | How the module achieves it |
|------|---------------------------|
| Identify the macro market regime | Classifies every trading day into one of 4 regimes using moving averages and the Gold/Nifty ratio |
| Provide actionable allocation | Returns concrete percentage splits across Equity, Gold, and Cash |
| Warn before drawdowns | Generates tiered exit signals (L1 Warning → L2 Strong Exit → L3 Full Exit) |
| Quantify strategy performance | Back-tests a regime-switching strategy vs. buy-and-hold and a 60/40 blend |
| Serve as a reusable component | Clean separation between data fetching, analysis, REST API, and UI |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      iWealthBuilder App                          │
│                                                                  │
│  ┌───────────────────────┐    ┌──────────────────────────────┐  │
│  │  Streamlit Dashboard  │    │  FastAPI REST API            │  │
│  │  pages/global_regime  │    │  global_regime_api/api.py    │  │
│  └──────────┬────────────┘    └─────────────┬────────────────┘  │
│             │                               │                   │
│             └──────────────┬────────────────┘                   │
│                            ▼                                     │
│            ┌───────────────────────────────┐                    │
│            │     RegimeAnalyzer            │                    │
│            │  (regime_analyzer.py)         │                    │
│            │                               │                    │
│            │  • calculate_indicators()     │                    │
│            │  • identify_regimes()         │                    │
│            │  • generate_exit_signals()    │                    │
│            │  • backtest_performance()     │                    │
│            │  • get_current_status()       │                    │
│            │  • get_performance_metrics()  │                    │
│            └──────────────┬────────────────┘                    │
│                           │ pandas DataFrame                     │
│                           ▼                                     │
│            ┌───────────────────────────────┐                    │
│            │     DataFetcher               │                    │
│            │  (data_fetcher.py)            │                    │
│            │                               │                    │
│            │  • fetch_data()               │                    │
│            │  • Intelligent CSV cache      │                    │
│            └──────────────┬────────────────┘                    │
│                           │                                     │
│             ┌─────────────┴─────────────┐                       │
│             ▼                           ▼                       │
│     Yahoo Finance (GC=F)        Yahoo Finance (^NSEI)           │
│     Gold Futures                Nifty 50 Index                  │
└─────────────────────────────────────────────────────────────────┘
```

### File Layout

```
iWealthBuilder/
│
├── global_regime_modules/          # Core analysis package
│   ├── __init__.py
│   ├── data_fetcher.py             # Data sourcing and caching
│   ├── regime_analyzer.py          # All analytical logic
│   ├── examples.py                 # Runnable usage examples
│   └── cache/                      # Auto-created CSV cache directory
│       └── data_cache.csv
│
├── global_regime_api/              # REST API package
│   ├── __init__.py
│   └── api.py                      # FastAPI application
│
└── pages/
    └── global_regime.py            # Streamlit UI page
```

---

## 3. The Four Market Regimes

The module recognises exactly **four mutually exclusive market regimes**, defined by the direction of Gold and Nifty relative to their 50-day moving averages and the trend of the Gold/Nifty ratio.

### Regime Summary Table

| Regime | Nifty Trend | Gold Trend | Ratio Trend | Meaning |
|--------|------------|-----------|------------|---------|
| **RISK_ON** | ↑ Above MA50 | ↓ Below MA50 | ↓ Falling | Equities are favoured; investors are taking risk |
| **RISK_OFF** | ↓ Below MA50 | ↑ Above MA50 | ↑ Rising | Safe-haven demand; capital rotating to Gold |
| **STRESS** | ↓ Below MA50 | ↓ Below MA50 | — | Both assets declining; maximum uncertainty |
| **LIQUIDITY_BOOM** | ↑ Above MA50 | ↑ Above MA50 | — | Excess liquidity driving both assets higher |

### Regime Colour Coding (used throughout UI)

| Regime | Hex Colour | Meaning |
|--------|-----------|---------|
| RISK_ON | `#2ecc71` Green | Positive for equities |
| RISK_OFF | `#f39c12` Amber | Defensive / Gold-favoured |
| STRESS | `#e74c3c` Red | Risk-off, both assets weak |
| LIQUIDITY_BOOM | `#3498db` Blue | Both assets strong |

---

## 4. Module: `data_fetcher.py` — DataFetcher

### Purpose

Responsible for **fetching, caching, and incrementally updating** daily closing price data for Gold (GC=F) and the Nifty 50 (^NSEI) from Yahoo Finance using the `yfinance` library. It avoids redundant network calls by maintaining a local CSV cache.

### Class: `DataFetcher`

```python
class DataFetcher:
    def __init__(self, cache_file='data_cache.csv')
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_file` | `str` | `'data_cache.csv'` | Name of the CSV file used for caching. Stored in a `cache/` subdirectory next to the module. |

---

### Methods

#### `fetch_data(start_date, end_date, force_refresh)`

Entry point for obtaining price data.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | `str` | `'2016-01-01'` | ISO date string for the beginning of the data range |
| `end_date` | `str` | `None` (today) | ISO date string for the end of the data range |
| `force_refresh` | `bool` | `False` | When `True`, deletes and re-downloads all data |

**Returns:** `pandas.DataFrame` with columns `Gold` and `Nifty`, indexed by `datetime`.

**Cache Logic (decision tree):**

```
fetch_data() called
      │
      ├─ force_refresh=True  ──► _fetch_fresh_data()  ──► save cache ──► return
      │
      └─ cache exists?
            │
            ├─ No  ──► _fetch_fresh_data()  ──► save cache ──► return
            │
            └─ Yes ──► _update_cached_data()
                              │
                              ├─ Cache up to date? ──► return cached subset
                              │
                              └─ Gaps detected?
                                    ├─ Earlier data needed ──► fetch earlier range
                                    ├─ Newer data needed   ──► fetch newer range
                                    └─ Merge, dedup, save, return
```

---

#### `_fetch_fresh_data(start_date, end_date)`

Downloads a complete date range for both Gold and Nifty, creates a combined DataFrame, forward-fills any missing values caused by different trading calendars (e.g. Indian vs. US holidays), and writes the result to the cache file.

#### `_update_cached_data(start_date, end_date)`

Loads the existing cache and identifies whether data is missing at the **beginning** (requested `start_date` is before the first cached date) or at the **end** (requested `end_date` is after the last cached date). Fetches only the missing segments and merges them with the existing cache.

#### `_fetch_date_range(start, end)`

Low-level helper that downloads Gold (`GC=F`) and Nifty (`^NSEI`) data for a specific range via `yfinance`. Handles exceptions gracefully and returns an empty `DataFrame` on failure.

#### `clear_cache()`

Deletes the local cache file. Subsequent calls to `fetch_data()` will re-download everything.

#### `get_cache_info()`

Returns a dictionary describing the current state of the cache:

```python
{
    'exists': True,
    'path': '/path/to/cache/data_cache.csv',
    'rows': 2340,
    'start_date': '2016-01-04',
    'end_date': '2025-03-28',
    'size_mb': 0.32
}
```

### Data Sources

| Asset | Yahoo Finance Ticker | Description |
|-------|---------------------|-------------|
| Gold | `GC=F` | Front-month Gold Futures (USD/oz) |
| Nifty 50 | `^NSEI` | NSE Nifty 50 Index (INR) |

> **Note:** Gold is quoted in USD per troy ounce; Nifty in INR points. Both are used in their native units for ratio calculations.

---

## 5. Module: `regime_analyzer.py` — RegimeAnalyzer

### Purpose

Pure analysis module — **no data fetching**. Accepts a DataFrame from `DataFetcher` and computes technical indicators, regime labels, exit signals, backtest returns, and performance statistics.

### Class: `RegimeAnalyzer`

```python
class RegimeAnalyzer:
    def __init__(self, data: pd.DataFrame)
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `pd.DataFrame` | DataFrame with `Gold` and `Nifty` columns, `datetime` index. Typically the output of `DataFetcher.fetch_data()`. |

---

### 5.1 Technical Indicators

Computed by `calculate_indicators()`. The method enriches the internal DataFrame with the following columns:

| Column | Formula | Purpose |
|--------|---------|---------|
| `Ratio` | `Gold / Nifty` | Core cross-asset ratio |
| `Ratio_MA50` | 50-day rolling mean of `Ratio` | Trend filter for the ratio |
| `Ratio_MA200` | 200-day rolling mean of `Ratio` | Long-term trend of the ratio |
| `Gold_MA50` | 50-day rolling mean of `Gold` | Gold medium-term trend |
| `Gold_MA200` | 200-day rolling mean of `Gold` | Gold long-term trend |
| `Nifty_MA50` | 50-day rolling mean of `Nifty` | Nifty medium-term trend |
| `Nifty_MA200` | 200-day rolling mean of `Nifty` | Nifty long-term trend |
| `Gold_Uptrend` | `Gold > Gold_MA50` | Boolean: Gold above its 50-day MA |
| `Nifty_Uptrend` | `Nifty > Nifty_MA50` | Boolean: Nifty above its 50-day MA |
| `Ratio_Above_MA` | `Ratio > Ratio_MA50` | Boolean: Ratio above its 50-day MA |
| `Gold_RSI` | RSI(14) of Gold | Momentum / overbought-oversold |
| `Nifty_RSI` | RSI(14) of Nifty | Momentum / overbought-oversold |
| `Gold_ROC` | 14-day % change in Gold | Rate of change |
| `Nifty_ROC` | 14-day % change in Nifty | Rate of change |
| `Correlation` | 20-day rolling correlation of Gold and Nifty daily returns | Measures co-movement |

#### RSI Calculation (`_calculate_rsi`)

Uses the standard Wilder smoothing method:

```
delta   = price.diff()
gain    = rolling_mean(max(delta, 0), period)
loss    = rolling_mean(max(-delta, 0), period)
RS      = gain / loss
RSI     = 100 - (100 / (1 + RS))
```

---

### 5.2 Regime Classification Logic

Computed by `identify_regimes()`. Each row is classified via the `classify_regime` function, which evaluates three booleans:

- `nifty_up` — Is Nifty above its 50-day MA?
- `gold_up` — Is Gold above its 50-day MA?
- `ratio_up` — Is the Gold/Nifty ratio above its 50-day MA?

**Decision rules (evaluated in priority order):**

```
1. nifty_up=False AND gold_up=False                     → STRESS
2. nifty_up=True  AND gold_up=True                      → LIQUIDITY_BOOM
3. gold_up=True   AND nifty_up=False AND ratio_up=True  → RISK_OFF  (primary)
4. nifty_up=True  AND gold_up=False  AND ratio_up=False → RISK_ON   (primary)
5. nifty_up=True  AND ratio_up=False                    → RISK_ON   (secondary)
6. gold_up=True   AND ratio_up=True                     → RISK_OFF  (secondary)
7. ratio_up=True                                        → RISK_OFF  (fallback)
8. ratio_up=False                                       → RISK_ON   (default)
```

> **Design note:** Rules 1 and 2 (both-down and both-up) take precedence over ratio direction. When only one asset is trending, the ratio acts as the tiebreaker.

---

### 5.3 Exit Signal Logic

Computed by `generate_exit_signals()`. Three-tier severity system for both Equity and Gold positions:

#### Equity Exit Signals

| Signal | Column | Condition | Action |
|--------|--------|-----------|--------|
| Level 1 — Warning | `Equity_Exit_L1` | `Nifty_RSI > 70` AND `Ratio > Ratio_MA50`, **OR** current regime is `RISK_OFF` | Reduce equity exposure, review |
| Level 2 — Strong Exit | `Equity_Exit_L2` | L1 is active AND `Nifty < Nifty_MA50` AND `Gold_Uptrend` | Significantly reduce equity |
| Level 3 — Full Exit | `Equity_Exit_L3` | Current regime is `STRESS` | Exit equity entirely, move to cash |

#### Gold Exit Signals

| Signal | Column | Condition | Action |
|--------|--------|-----------|--------|
| Level 1 — Warning | `Gold_Exit_L1` | `Gold_RSI > 75` AND `Ratio < Ratio_MA50`, **OR** current regime is `RISK_ON` | Reduce gold exposure, review |
| Level 2 — Strong Exit | `Gold_Exit_L2` | L1 is active AND `Gold < Gold_MA50` AND `Nifty_Uptrend` | Significantly reduce gold |
| Level 3 — Full Exit | `Gold_Exit_L3` | Regime is `RISK_ON` AND `Gold < Gold_MA200` | Exit gold entirely |

---

### 5.4 Backtesting & Performance

#### `backtest_performance()`

Simulates a **regime-switching strategy** alongside three benchmarks:

| Strategy | Logic |
|----------|-------|
| Buy & Hold Nifty | 100% allocation to Nifty throughout |
| Buy & Hold Gold | 100% allocation to Gold throughout |
| **Regime Strategy** | RISK_ON → 100% Nifty; RISK_OFF → 100% Gold; LIQUIDITY_BOOM → 50% Nifty + 50% Gold; STRESS → 100% Cash (0% return) |
| 60/40 Portfolio | 60% Nifty + 40% Gold, rebalanced daily |

All four strategies produce cumulative return series stored as:
`Nifty_Cumulative`, `Gold_Cumulative`, `Strategy_Cumulative`, `Portfolio_60_40_Cumulative`

#### `get_performance_metrics()`

Calculates and returns a dictionary containing:

| Metric | Description |
|--------|-------------|
| `period_years` | Total years in the analysis window |
| `total_returns` | Percentage total return per strategy |
| `annualized_returns` | CAGR per strategy |
| `volatility` | Annualised standard deviation of daily returns (× √252) |
| `sharpe_ratio` | `(annual_return - 6%) / volatility` (risk-free rate = 6%) |
| `max_drawdown` | Maximum peak-to-trough decline during the period |

#### `analyze_regime_statistics()`

Returns a DataFrame with per-regime statistics:

| Column | Description |
|--------|-------------|
| `Regime` | Regime name |
| `Days` | Number of calendar days spent in this regime |
| `Percentage` | Proportion of the total analysis window |
| `Avg_Nifty_Return_%` | Average daily Nifty return while in this regime |
| `Avg_Gold_Return_%` | Average daily Gold return while in this regime |
| `Nifty_Volatility_%` | Annualised Nifty volatility in this regime |
| `Gold_Volatility_%` | Annualised Gold volatility in this regime |

#### `get_regime_changes()`

Returns a DataFrame of every date where the regime transitioned, with columns: `Regime`, `Previous_Regime`, `Nifty`, `Gold`, `Ratio`.

---

### 5.5 Asset Allocation Recommendations

`_get_allocation_recommendation(regime)` returns a dictionary for the current regime:

| Regime | Nifty % | Gold % | Cash % | Description |
|--------|---------|--------|--------|-------------|
| `RISK_ON` | 70% | 20% | 10% | Favour equities — market in risk-on mode |
| `RISK_OFF` | 30% | 60% | 10% | Favour gold — defensive positioning |
| `STRESS` | 0% | 0% | 100% | Move to cash — both assets declining |
| `LIQUIDITY_BOOM` | 60% | 30% | 10% | Both assets rising — prefer equities |

---

### `get_current_status()`

Returns a comprehensive snapshot of the current market state:

```python
{
    'current_regime':        'RISK_ON',
    'regime_start_date':     '2025-01-15',
    'days_in_regime':        74,
    'current_nifty':         23500.0,
    'current_gold':          2950.0,
    'current_ratio':         0.1255,
    'nifty_change_pct':      4.2,
    'gold_change_pct':       -1.1,
    'nifty_rsi':             58.3,
    'gold_rsi':              42.7,
    'correlation':           0.12,
    'equity_exit_l1':        False,
    'equity_exit_l2':        False,
    'equity_exit_l3':        False,
    'gold_exit_l1':          True,
    'gold_exit_l2':          False,
    'gold_exit_l3':          False,
    'recommended_allocation': {
        'nifty_pct': 70,
        'gold_pct':  20,
        'cash_pct':  10,
        'description': 'Favour equities - market in risk-on mode'
    },
    'last_updated': '2025-03-28'
}
```

---

### `run_analysis()` — Full Pipeline

Convenience method that runs all analysis steps in sequence:

```python
analyzer.calculate_indicators()   # Step 1: Compute MAs, RSI, ROC, Correlation
analyzer.identify_regimes()        # Step 2: Label each row with a regime
analyzer.generate_exit_signals()   # Step 3: Compute tiered exit signals
analyzer.backtest_performance()    # Step 4: Simulate strategy returns
```

---

## 6. Module: `global_regime_api/api.py` — FastAPI REST API

A **FastAPI** application exposing the regime analysis as a set of JSON endpoints. It maintains an in-memory analyzer cache that is refreshed automatically when data is more than one day old.

### Running the API

```bash
python global_regime_api/api.py
# or
uvicorn global_regime_api.api:app --host 0.0.0.0 --port 8085
```

Interactive docs are available at `http://localhost:8085/docs`.

### In-Memory Cache

```python
_analyzer_cache = {
    'analyzer': None,       # RegimeAnalyzer instance
    'last_update': None     # datetime of last refresh
}
```

`get_analyzer(force_refresh=False)` checks whether the cache is stale (> 1 day old) and re-initialises it if needed.

---

### API Endpoints

#### `GET /`
Root endpoint. Returns a directory of all available endpoints.

---

#### `GET /api/current`

Returns the current regime status including prices, RSI values, exit signals, and recommended allocation.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `refresh` | `bool` | `false` | Force a fresh data download |

**Example response:**
```json
{
  "status": "success",
  "data": {
    "current_regime": "RISK_ON",
    "regime_start_date": "2025-01-15",
    "days_in_regime": 74,
    "current_nifty": 23500,
    "current_gold": 2950,
    ...
  },
  "timestamp": "2025-03-28T10:00:00"
}
```

---

#### `GET /api/regimes`

Returns the history of regime transitions.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `int` | `null` (all) | Return only the N most recent transitions |
| `regime_type` | `str` | `null` | Filter to a single regime, e.g. `STRESS` |

---

#### `GET /api/performance`

Returns comprehensive performance metrics for all strategies.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `refresh` | `bool` | `false` | Force data refresh |

---

#### `GET /api/regime-stats`

Returns per-regime statistics (average returns, volatility, number of days).

---

#### `GET /api/data`

Returns historical daily data with regime labels and technical indicators.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | `str` | `null` | Filter from this date (YYYY-MM-DD) |
| `end_date` | `str` | `null` | Filter to this date (YYYY-MM-DD) |
| `limit` | `int` | `100` | When no date range is given, return the last N days |

**Columns returned:** `Gold`, `Nifty`, `Regime`, `Gold_MA50`, `Nifty_MA50`, `Ratio`, `Ratio_MA50`, `Gold_RSI`, `Nifty_RSI`, `Correlation`.

---

#### `GET /api/allocation`

Returns the current recommended portfolio allocation with regime context.

---

#### `POST /api/refresh`

Forces a complete data refresh, clearing the in-memory cache and re-downloading from Yahoo Finance.

---

#### `GET /health`

Health-check endpoint. Returns the last available data date and cache age in hours.

---

## 7. Module: `pages/global_regime.py` — Streamlit Dashboard

An interactive **Streamlit** web page that exposes the full analysis as a visual dashboard. It is accessed via the main iWealthBuilder app as a page.

### Running the dashboard

```bash
streamlit run iWealthBuilder_app_final.py
# Then navigate to the "Global Regime" page in the sidebar
```

### UI Layout

```
┌──────────────────────────────────────────────────────┐
│  Sidebar                                             │
│  ├─ Start Date picker                               │
│  ├─ Force Refresh checkbox                          │
│  ├─ Reload Analysis button                          │
│  ├─ Regime legend                                   │
│  └─ About section                                   │
├──────────────────────────────────────────────────────┤
│  Header: Gold/Nifty Regime Analysis                  │
│                                                      │
│  Tab 1: 📊 Dashboard                                 │
│  ├─ Current Regime card (colour-coded)              │
│  ├─ Nifty & Gold metrics with regime % change       │
│  ├─ RSI values                                      │
│  ├─ Gold/Nifty Ratio                                │
│  ├─ Recommended Allocation (Nifty / Gold / Cash)    │
│  └─ Tiered Exit Signals (Equity + Gold)             │
│                                                      │
│  Tab 2: 📈 Charts (Plotly 6-panel chart)            │
│  ├─ Panel 1: Gold & Nifty prices + regime shading   │
│  ├─ Panel 2: Gold/Nifty Ratio vs 50d & 200d MA      │
│  ├─ Panel 3: Nifty RSI / Gold RSI                   │
│  ├─ Panel 4: Cumulative returns (4 strategies)      │
│  ├─ Panel 5: Regime distribution bar / Correlation  │
│  └─ Panel 6: Performance table / Regime stats table │
│                                                      │
│  Tab 3: 📅 Regime History                            │
│  ├─ Colour-coded table of all regime periods        │
│  │   (Start date, End date, Days, Nifty %, Gold %)  │
│  └─ Download CSV button                             │
│                                                      │
│  Tab 4: 📉 Performance Metrics                       │
│  ├─ Top-level total return cards                    │
│  └─ Detailed metrics table (CAGR, Vol, Sharpe, DD)  │
└──────────────────────────────────────────────────────┘
```

### `load_data(start_date, force_refresh)`

Streamlit-cached function (`@st.cache_data(ttl=3600)`) that orchestrates data fetching and analysis. Result is cached for 1 hour to avoid redundant computations on page reloads.

### `create_comprehensive_chart(analyzer)`

Builds a 6-row, 2-column **Plotly** subplot figure. Key features:
- Regime periods are shaded as coloured rectangles in the background of every time-series panel using `layout.shapes`.
- Uses a secondary Y-axis for Gold prices (since Gold is in USD and Nifty is in INR, the scales differ greatly).
- RSI panels include dashed horizontal lines at the overbought/oversold thresholds.

---

## 8. Data Flow

```
1. User requests data (start_date, force_refresh)
         │
         ▼
2. DataFetcher.fetch_data()
   ├── Cache hit & up-to-date?  ──► Return cached DataFrame
   └── Cache miss / stale?      ──► Download from Yahoo Finance
                                     ├── GC=F  (Gold Futures)
                                     └── ^NSEI (Nifty 50)
                                    Forward-fill, merge, save cache
         │
         ▼ DataFrame: columns=[Gold, Nifty], index=datetime
3. RegimeAnalyzer.__init__(data)
         │
         ▼
4. RegimeAnalyzer.run_analysis()
   ├── calculate_indicators()
   │    └── Adds: Ratio, MAs, RSI, ROC, Correlation (14 new columns)
   ├── identify_regimes()
   │    └── Adds: Regime (one of 4 labels)
   ├── generate_exit_signals()
   │    └── Adds: 6 boolean exit signal columns
   └── backtest_performance()
        └── Adds: Returns and cumulative return series (8 new columns)
         │
         ▼
5. Output consumed by:
   ├── Streamlit dashboard  (interactive charts + metrics)
   ├── FastAPI endpoints    (JSON responses)
   └── Direct Python usage  (examples.py, custom scripts)
```

---

## 9. Usage Examples

### Quick Start

```python
from global_regime_modules.data_fetcher import DataFetcher
from global_regime_modules.regime_analyzer import RegimeAnalyzer

# 1. Fetch data (uses cache if available)
fetcher = DataFetcher()
data = fetcher.fetch_data(start_date='2020-01-01')

# 2. Run analysis
analyzer = RegimeAnalyzer(data)
analyzer.run_analysis()

# 3. Get current regime
status = analyzer.get_current_status()
print(f"Current regime: {status['current_regime']}")
print(f"Recommended: {status['recommended_allocation']}")
```

### Get Performance Metrics

```python
metrics = analyzer.get_performance_metrics()

print(f"Strategy CAGR:  {metrics['annualized_returns']['regime_strategy']:.2f}%")
print(f"Nifty CAGR:     {metrics['annualized_returns']['nifty']:.2f}%")
print(f"Strategy Sharpe:{metrics['sharpe_ratio']['regime_strategy']:.2f}")
print(f"Max Drawdown:   {metrics['max_drawdown']['regime_strategy']:.2f}%")
```

### Analyse Per-Regime Statistics

```python
stats = analyzer.analyze_regime_statistics()
print(stats[['Regime', 'Days', 'Percentage', 'Avg_Nifty_Return_%', 'Avg_Gold_Return_%']])
```

### Inspect Recent Regime Transitions

```python
changes = analyzer.get_regime_changes()
print(changes.tail(10))
```

### Force a Data Refresh

```python
fetcher = DataFetcher()
data = fetcher.fetch_data(force_refresh=True)
```

### Cache Management

```python
# Check cache status
info = fetcher.get_cache_info()
print(f"Cache: {info['rows']} rows from {info['start_date']} to {info['end_date']}")

# Clear cache
fetcher.clear_cache()
```

### Export Analysed Data to CSV

```python
analyzer.data.to_csv('regime_analysis_output.csv')
```

### Call the REST API

```bash
# Current regime
curl http://localhost:8085/api/current

# Last 20 regime transitions
curl "http://localhost:8085/api/regimes?limit=20"

# Performance metrics
curl http://localhost:8085/api/performance

# Recent 5 days of data
curl "http://localhost:8085/api/data?limit=5"

# Force refresh
curl -X POST http://localhost:8085/api/refresh
```

---

## 10. Configuration Reference

### Default Parameters at a Glance

| Parameter | Location | Default | Notes |
|-----------|----------|---------|-------|
| Cache file name | `DataFetcher.__init__` | `data_cache.csv` | Stored in `global_regime_modules/cache/` |
| Default start date | `DataFetcher.fetch_data` | `'2016-01-01'` | Earlier dates require more API calls |
| MA short window | `RegimeAnalyzer.calculate_indicators` | 50 days | Used for trend signals |
| MA long window | `RegimeAnalyzer.calculate_indicators` | 200 days | Used for Gold exit L3 |
| RSI period | `RegimeAnalyzer._calculate_rsi` | 14 days | Standard setting |
| ROC period | `RegimeAnalyzer.calculate_indicators` | 14 days | Rate of change lookback |
| Correlation window | `RegimeAnalyzer.calculate_indicators` | 20 days | Rolling correlation |
| Equity overbought RSI | `generate_exit_signals` | 70 | L1 equity exit trigger |
| Gold overbought RSI | `generate_exit_signals` | 75 | L1 gold exit trigger |
| Risk-free rate | `get_performance_metrics` | 6% | Used in Sharpe calculation |
| API cache TTL | `global_regime_api/api.py` | 1 day | Re-fetches after 24 hours |
| UI cache TTL | `pages/global_regime.py` | 3600 s | Streamlit `@st.cache_data` |
| API port | `global_regime_api/api.py` | 8085 | FastAPI server port |

---

*Documentation generated from source code analysis of the `global_regime_modules`, `global_regime_api`, and `pages/global_regime.py` modules.*
