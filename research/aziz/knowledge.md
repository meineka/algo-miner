# Andrew Aziz — Knowledge Base

Living document of everything we know about Andrew Aziz's day-trading
methodology. Updated incrementally by the `aziz-research` loop (see
`scripts/aziz_research_tick.md`).

**Convention:** Add new findings at the bottom of the matching section
with a date-stamped entry, e.g. `### 2026-05-14`. Never rewrite or
delete prior entries — older facts are still source-of-truth.

---

## 1. Person

- Andrew Aziz, Canadian. Former chemical engineer.
- Founded **Bear Bull Traders** (BBT) in 2015/2016.
- YouTube channel: `UCfO2yCpx6_XU-xovhpJuaYw` (Bear Bull Traders, ~600 K subs).
- Investopedia "Best Day Trading Course of the Year" since 2021.
- Co-author with Carlo Zarattini and Andrea Barbon (Prof of Finance,
  University of St. Gallen) on academic SSRN papers since 2023.

## 2. Books

| Title | Year | Source |
|---|---|---|
| How to Day Trade for a Living | 2016 | bestseller in 20 languages |
| Advanced Techniques in Day Trading | 2018 | sequel |

## 3. Universe — "Stocks in Play" (pre-market selection)

Filters Aziz applies before market open to build his watchlist:

| Filter | Threshold |
|---|---|
| Gap (up or down) | ≥ **2 %** vs. prior close |
| Pre-market volume | ≥ **50 000** shares |
| Average Daily Volume | > **500 000** |
| ATR | ≥ **0,50 USD** |
| Fundamental catalyst | required (earnings / FDA / guidance / M&A) |

### Float classification

| Float | Price band | Preferred strategies |
|---|---|---|
| Low < 20 M | < 10 USD | Bull Flag, Fallen Angel |
| Medium 20 – 500 M | 10 – 100 USD | **Aziz's favourite** — all strategies |
| Large > 500 M | > 20 USD | Trend, ABCD, VWAP |

> *"Medium float stocks in the $10-$100 price range are my favourite!"*

## 4. Strategies

### 4.1 Opening Range Breakout (ORB)
- Range = **first 5-min candle** (academic paper version); also tested 15-min, 30-min.
- 1st candle green → buy at open of 2nd candle. Red → short.
- Stop = opposite side of the range candle (high for short, low for long).
- Profit target = **10R** OR close at end-of-day.
- 1 % portfolio risk, 4× leverage (US broker).
- Aziz quote: *"The Opening Range Breakout (ORB) strategy is my bread and butter for trading the market open."*
- Backtest on **top 20 "Stocks in Play"** (Zarattini/Barbon/Aziz 2024):
  total net return **> 1 600 %**, Sharpe **2,81**, alpha **36 %/yr**, vs. S&P-500 **+198 %** same period.

### 4.2 VWAP
- Aziz quote: *"VWAP is my favourite indicator."*
- Long when price reclaims VWAP from below with a confirming bullish bar.
- Short when price loses VWAP from above (especially after 10:30 a.m. = "late-morning weakness").
- Stop = the other side of VWAP.
- VWAP also used as a profit-take level on counter-trend trades.

### 4.3 Bull Flag Momentum
- Flagpole: strong impulse (1.5 hours after the Open is the sweet spot).
- Consolidation: pullback retraces ≤ 50 % of pole and stays above VWAP.
- Entry: new high break of the flag with volume.
- *"Never trade Bull Flag Momentum mid-day or near close."*
- Bear-flag mirror works the same way.

### 4.4 ABCD Pattern
- A = day high (impulse). B = pullback low. C = consolidation near B. D = re-entry break above C/B.
- Valid retrace zone = 38.2 – 61.8 % of A-impulse.
- Inverse ABCD for shorts.

### 4.5 Red-to-Green (and Green-to-Red)
- Stock opens below prior-day close (red) and reclaims it (green) with volume.
- Entry: 1-min candle closes above the prior-day close + rising volume.
- Stop: below morning low or below VWAP, whichever is tighter.
- Best window: first **60–90 minutes** of the session.

### 4.6 Moving-Average Trend (9 / 20 EMA)
- 9 EMA > 20 EMA in uptrend, both rising, price above both.
- Entry on pullback to the 9-or-20 EMA band, with confirming bullish bar.
- Exit hint: **break of the 20 EMA** (Aziz: "20 EMA is usually a stronger support/resistance, wait for it").
- Trail along the 9 EMA, add on additional pullbacks if VWAP still holds.

### 4.7 Top / Bottom Reversal
- Exhaustion at session extremes + reversal candle + EMA cross.
- Mostly counter-trend; needs confluence (RSI extreme + VWAP loss + volume drop).

### 4.8 Support / Resistance Trade
- Pre-marked levels: prior-day high / low, prior-day close, key round numbers.
- Trade off bounces with VWAP confirmation.

## 5. Risk & Money Management

| Rule | Value |
|---|---|
| Risk per trade | ≤ **1 %** of account |
| Daily loss stop | **2 %** of account (Aziz: "walk away") |
| Consecutive loss cutoff | **3 strikes** → done for the day |
| R:R minimum | **2:1** (academic paper uses 10:1 for ORB targets) |
| Position sizing | linear in stop distance |
| Trading journal | mandatory |
| Time-of-day filter | mostly first 1–2 h after Open; avoid 11:30 – 14:30 chop |

## 6. Notable interviews / lectures (YouTube)

| Title | Video ID | Notes |
|---|---|---|
| The Most Traded Strategy by Andrew Aziz (2023) | `PFnvcZ_ni3I` | ORB + Stocks in Play |
| [2024] Day Trading For Beginners — Ultimate Full Guide | `7gLocbf6Lto` | full course |
| Complete Day Trading Beginners Guide | `6-eEj8g6xdI` | overview |
| How He Became A Full-Time Day Trading Legend | `MmQdPu7JYHk` | biography |
| Secrets of Day Trading For A Living | `4T8vxEWgTLs` | interview |
| The Consistently Profitable Day Trader (2022) | `fbeUeCtpFOg` | interview |
| Full-Time Day Trader — SECRETS and TRICKS | `S1i8wlQVNYY` | interview |
| VWAP Trading Strategies with Brian Shannon | `ADFMxPaqhQo` | joint webinar |
| Webinar: How to Trade Using the VWAP | `cimqvvFtJbY` | VWAP deep-dive |
| Andrew Aziz Day Trading Course — Beginners | `ePe7VbQumOg` | brokers / platforms |
| So You Want to Day Trade for a Living? | `YGbt_3vnnhk` | mindset |
| Powerful Day Trading Strategy and Entry | `c_fX5srrMqo` | entry tactics |
| How to Day Trade for a Living — Summary | `yBRLLj_WthY` | book summary |

## 7. Academic papers (SSRN)

| Paper | Year | SSRN ID |
|---|---|---|
| Can Day Trading Really Be Profitable? | 2023 | `4416622` |
| Volume Weighted Average Price (VWAP) The Holy Grail | 2023 | `4631351` |
| A Profitable Day Trading Strategy For The U.S. Equity Market | 2024 | `4729284` |

## 8. Direct Aziz quotes (verified)

> "After I build my watchlist in the morning, I closely monitor the
> shortlisted stocks in the first five minutes after the Open. I
> identify their opening range and their price action. The stocks
> will either move higher or below the VWAP."

> "I usually use loss or break of VWAP."

> "The Opening Range Breakout (ORB) strategy is my bread and butter
> for trading the market open."

> "Bull Flag Momentum trades tend to be the best strategies for the
> open (first 1.5 hours); never trade Bull Flag Momentum in mid-day
> or at close."

> "Medium float stocks in the $10-$100 price range are my favourite!"

> "20 EMA is usually a stronger support or resistance, so it is
> better to wait for that."

## 9. Open research questions (for the loop to chase)

- Exact ATR-stop multipliers Aziz uses for each strategy.
- Cut-off rules between Aziz's strategies and his "Reversal Trade".
- Position-sizing details for "Angels" (low-float gappers).
- Specific scanner parameters (Trade-Ideas / Finviz / DAS) he recommends.
- His view on extended-hours / pre-market entries.
- Performance attribution between his five core strategies.
- How he handles overnight gaps in held positions (he doesn't hold overnight).
- His take on options vs. equities for the same setups.
- Updated 2025/2026 research papers, if any.

---

## Change log

### 2026-05-14 — seeded
- Initial knowledge base from web search snippets (YouTube direct
  fetch blocked by sandbox egress proxy).
- Sources: WebSearch summaries of Goodreads quotes, Shortform
  overviews, BBT Session 4 PDF excerpts (not downloadable —
  `host_not_allowed`), SSRN paper abstracts, Alphatrends podcast
  description, Wikipedia.

### 2026-05-14 — Angels & low-float position sizing

- **Angel definition:** *"An Angel is a low float stock (usually less
  than twenty million shares) that has gapped up significantly due
  to important fundamental news."* (BBT)
- Low-float gappers (< 10–20 M shares) produce the **largest
  percentage runners** but are the most volatile, most prone to
  violent reversals, and have the **widest spreads**.
- Aziz position-sizing rule for Angels: *"Your position size should be
  dramatically smaller on a stock with a 5-million-share float than
  on a stock with a 100-million-share float. The same dollar risk
  means fewer shares."*
- Source: WebSearch snippets from *Advanced Techniques in Day
  Trading* (Shortform summary) and BBT teaching materials. Exact
  formula not in indexed snippets — only the qualitative rule.

### 2026-05-14 — ATR stop multipliers

- No Aziz-specific ATR multiplier surfaced in the indexed snippets
  beyond the general 1.5–2.0 range used across the trading
  community. Aziz mostly uses **structural stops** (VWAP, 9/20 EMA,
  range candle high/low) rather than ATR-multiplied stops.
- Sandbox WebSearch returns only generic "ATR × 1.5 default"
  guidance, not Aziz primary-source numbers.

### Open follow-ups for next ticks
- Exact share-size formula for Angel trades (book chapter reference)
- VWAP-stop-loss exit rules (immediate exit vs. close-of-candle)
- His view on partial profit-taking (½ at first target, run trailer?)
- 2025/2026 Zarattini × Aziz academic paper, if any

### 2026-05-14 17:00Z — partial profit-taking & trade management

Aziz **scales out** rather than holding a single position to a single target:

- Sells **½ position at first target** (typically point D in an ABCD,
  or a structural level like prior-day high / VWAP / a 9-EMA touch).
- **Stop moves to break-even immediately** after the partial fill.
- Rule: *"Never go red on a stock that you already booked some profit on."*
- Remaining ½ runs to second target OR until "sellers acquire control"
  / momentum visibly fades.
- Stop on the runner: discretionary structural — Aziz **does not use
  trailing-stop orders**, he watches the chart and exits manually.

ABCD-specific tier:
- 1st target ≈ 1:1 (at point D, the breakout level)
- 2nd target ≈ 2:1 or further (extension / next resistance)

Risk-reward floor: **minimum 2:1 win:lose** across all setups; ABCD
is the strict 1:1 / 2:1 tiered exit.

Implications for `algo-miner`:
- `Trade` could carry `tp1_price` / `tp1_size` in addition to single `tp_price`.
- After tp1 fill, `stop_price` is overwritten with `entry_price`.
- New genome knobs: `tp1_r_mult` (default 1.0) and `tp1_size_pct`
  (default 0.5).

### Open follow-ups (updated)
- Exact share-size formula for Angel trades (book chapter reference)
- VWAP-stop-loss exit rules (immediate exit vs. close-of-candle)
- 2025/2026 Zarattini × Aziz academic paper, if any
- His scanner tooling specifics (Trade-Ideas / Finviz / DAS filter strings)
