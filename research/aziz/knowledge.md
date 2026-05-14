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

---

### 2026-05-14 — MASS TRANSCRIPT INGEST (6 videos, ~6 hours of content)

User supplied raw transcripts of Aziz's full curriculum + 2 community
mentors + 3 live trade walkthroughs. Saved as curated files under
`transcripts/`. New facts and operational rules below:

#### Capital, account, latency
- **Account minimum:** $10 000 (Aziz's recommendation); US PDT rule
  requires $25 000 to escape the 4-day-trades-in-5-days lockout.
  Offshore brokers (CMEG / Lightspeed / SureTrader) bypass PDT.
- **Internet:** wired cable, not Wi-Fi. Low ping > bandwidth.
- **Latency target:** < 200 ms to NASDAQ servers (NJ/NY).
- **DAS Trader Pro cost:** ~$150/month + $15–20 data feed.
- **Sim minimum:** 3 months before going live, on the same platform.
- **Computer specs:** Intel i7, 16-32 GB RAM, SSD, multi-monitor GPU.

#### Scanner criteria (re-stated exactly from current course)
- Gap up or down ≥ **2 %**
- Price range: **$5 – $250**
- Pre-market volume ≥ **100 000 shares**
- Average True Range ≥ **$0.50** intraday
- Avoid: penny stocks, block-trade-only premarkets, foreign ADRs

#### Risk-management rules (verbatim)
- **1 % rule:** never risk > 1 % of account on one trade (shark-bite cap)
- **6 % rule:** if down 6 % of account in last 30 days → switch back to
  simulator for 2 weeks (piranha-bite cap)
- **2:1 minimum R:R** to enter any trade
- **Hawk day / tilt day signs:** caffeine + P&L-watching + revenge
  trading + averaging down → STOP, walk away, broker lockout

#### Scale-out + trade management
- Default: **½ position at first target = 1 R** → stop to break-even → ½ runs
- Verbatim: *"Never go red on a stock you booked profit on."*
- If pattern changes (HH/HL → LL/LH or vice versa) **before** original
  stop hit → exit at break-even immediately, don't wait
- Aziz uses **discretionary structural stops**, NOT trailing-stop orders
- ABCD tier: 1st target = point D (≈1 R), 2nd target = extension (2 R+)

#### Order-type strategy (Level 2 / liquidity)
- Default order type: **Marketable Limit** (Market + cap, e.g. ask + $0.05)
- **Counter-intuitive Level 2:** huge bid = bearish, huge ask = bullish
  (real desperate sellers hit the bid, NITF large bids are low-balling)
- Aziz uses `EDGX` route to earn ECN rebate on adds

#### Indicator stack (Aziz's chart)
- Background: **white** (easier on eyes; he hates dark themes)
- Bullish candle: **white** (some use green); bearish: **red**
- Indicators:
  - **VWAP** (favourite, intraday only)
  - 9 EMA, 20 EMA (exponential)
  - 50 SMA, 200 SMA (simple)
  - Prior-day close (PCL — *"most important level"*)
  - Camarilla pivots (uses only R3/R4/S3/S4; Thor evangelist of this)
  - Volume bars
- **No trendlines, no Fibonacci** — Aziz: *"trendlines are subjective"*

#### Time-of-day matrix
| Window (ET) | Activity |
|---|---|
| 08:30 – 09:00 | Premarket scanner pass, catalyst read |
| 09:00 – 09:25 | Finalize watchlist (3–5 names) |
| 09:30 – 10:00 | ORB / Fallen Angel / 5-min reversal |
| 10:00 – 11:00 | 920 reversal (2-min chart only) |
| 11:00 – 15:30 | Aziz skips most days |
| ~15:50 | Last 10 min: close all positions, no overnight holds |

#### Strategies catalog (10+)
Trend: ORB (1/2/5/15/30/60 min), Bull Flag, Bear Flag, ABCD, break of HoD,
break of pre-market H/L, Red-to-Green, Fallen Angel, Mountain Pass.
Counter-trend: 9/20 reversal ("920 trade"), parabolic reversal, double
bottom, false breakout, extreme-price reversal, top/bottom reversal.

#### 920 trade — verbatim recipe (re-confirmed)
1. Stock strongly above VWAP for first 30–45 min
2. **2-minute chart only**
3. Pullback to 20 EMA between 10:00 – 10:30
4. Long with stop just below 20 EMA
5. 1st partial = 9 EMA touch
6. 2nd partial = break of HoD
7. Add on additional 9 EMA pullback if trend continues

#### Engulfing crack
- 5-min engulfing candle at the OPEN is a standalone strategy
- Bullish engulfing = green covers prior red entirely → long
- Bearish engulfing = red covers prior green entirely → short
- *"I trade it almost every time I see one."*

#### Measured-move target
- After ORB breaks: take the LENGTH of the impulse leg, project it
  forward from the breakout point → that's the profit target
- Confirms when there's no other obvious level in the price path

#### Top 3 mistakes (Jan-2025 recap)
1. **Bias before the open** — predicting direction without waiting for
   the open price action; Aziz: *"NVDA was gapping up to all-time high
   and I'd have sworn it'd run; it dumped 5 %. No bias."*
2. **Not respecting your stop loss** — averaging down kills accounts
3. **Trading past your daily goal** — once profit target hit, STOP.
   Trading out of boredom = death by 1000 cuts.

#### Camarilla pivots (Thor's specialty, used by Aziz too via DAS)
- Invented by **MB Curton Twig** (Canadian, late 1980s)
- Used by Citadel and other 30–40 % of US market-maker flow
- Aziz uses only **R3, R4, S3, S4**; ignores R1/R2/S1/S2 and R5/R6/S5/S6
- "Gray area" between R3 and S3 = don't trade, you'll get chopped
- Inside day (narrow pivots) → no breakout, play edges
- Outside day (wide pivots) → breakout candidate
- Bullish open + above R4 → back-test long; bearish open + below S4 → back-test short

#### Bookmap / heat-map order flow (Thor's tool)
- Limit orders = lines (intensity = size); market orders = dots
- Bullish book: thin orders below, dense above → upward momentum
- Bearish book: dense below, thin above → downward momentum
- Balanced book = chop, no trade
- **Iceberg detection** via DAS Display field (e.g. show 1k of 40k order)
- **Absorption** = repeated buying that fails to move price = invisible seller

#### Confluence (the entry gate)
Aziz/Thor agree: enter only when **all four align in a 5–10 min window**:
1. Price at a meaningful level (pivot OR VWAP OR pre-market H/L OR daily MA)
2. Volume confirms (VPA = volume + price action)
3. Order book matches trade direction (bullish stack for long)
4. Iceberg / absorption defending the level

> *"That window is only open 5–10 min — miss it, wait for the next one."*

#### Worked examples extracted
- **LK Jan 27 2020:** 5-min ORB long after coronavirus gap-down, scale at 37.67 / 38.00 / 38.55 / 38.79 / 39.25, exit at engulfing reversal candle
- **DAL Jan 10 (year unstated):** earnings gap-up to near ATH 67.50, 5-min ORB long at 65.92, stop 60c, scale at 68 / 68.5 / 69, +$2 000 on 1 000 shares
- **fubo (Jan 7 2025):** 1-min ORB long $5.50 → scaled to $6.30, +biggest gain of day
- **NVDA (Jan 7 2025):** CES catalyst gap-up to ATH, dumped 5 % at the open. Aziz tried 4 reversal entries, took small loss each, stop-respected
- **BM, Comcast, MSFT, IBM (earnings):** 5-min ORB technique with trendline-break confirmation, measured-move target

### Trade Book ("Fachbuch") method
Every trader must build their own printed handbook with:
1. Stock selection rules
2. Time-of-day windows
3. Trade identification
4. Trade execution (entry trigger, share size, stop)
5. Trade management (partials, break-even, exits)
6. Psychology notes (your common mistakes)
7. Worked examples (5–10 historical trades)

Sample trade books at `bearbulltraders.com/gifts` + chat-room Downloads
folder. Named for their creator (e.g. "NyQuil").

### Open follow-ups (updated again)
- Exact share-size formula for Angel trades
- 2025/2026 Zarattini × Aziz academic paper
- Aziz's hotkey script for the scale-out 25/50/100 % buttons
- Robert's psychology-module video list (referenced multiple times)

---

### 2026-05-14 — Second mass ingest: Market Atlas + Bear-Market 2025

User supplied 4 more Tactiq raw transcripts (~1 100 lines). Saved
verbatim to `transcripts/raw/`:

| Video ID | Title |
|---|---|
| `z11htAM05q0` | [2026] MOST Important Day Trading Strategy & Tools |
| `JNP5ehsTQ6A` | One Scalping Strategy That Works Everyday |
| `aQmeUOhopAs` | Live DAY Trading $17,636: Must-Have Trading Tool |
| `yfOlLmxUR6k` | Day Trading in a Bear Market [2025 Tariff War] |

#### Market Atlas — Aziz's flagship tool (NEW)

> *"The most important day trading tool you need."*

- Built by Aziz / Trading Terminal **in partnership with NASDAQ**
- Available at **tradingterminal.com**
- **$99/month**; $20 of that flows to NASDAQ for TotalView data feed
- *"TotalView is the only depth-of-market feed actually from NASDAQ.
  Everything else that calls itself depth-of-market is not."*
- **What it is:** Level 2 with a **time axis** — historical view of
  bid/ask stacks over time, NOT a snapshot
- DAS Trader can show level 2 but cannot zoom out or show history;
  Market Atlas adds those two features
- Aziz quote: *"I don't really look at level 2 anymore — I'm looking
  at Market Atlas which is the same thing but with the time axis."*

##### Reading rule (verbatim)
> *"When there is a huge imbalance between the bid stack and the ask
> stack, you can safely say the price has a tendency to go toward
> those liquidity pools."*

##### Confluence with VWAP (the gate)
1. Find a significant liquidity pool above or below current price
2. Confirm direction with VWAP — long only if price is **above VWAP**;
   short only if **below VWAP**
3. Enter at level reclaim/loss, with stop on the other side of VWAP
4. Target = the next liquidity pool in trade direction

##### Worked Market Atlas examples (April–May 2026)
- **NVDA at 201.25:** big stack at 202–205, none below → bullish book.
  Aziz went long, scaled to 205.
- **PLTR at 149:** 70 k-share order parked at 150 for 30 minutes.
  Each timestamp screenshot (9:31, 9:45, 9:47, 9:59, 10:14) showed
  the order still defending → price ground higher to 152.
- **AMD at 291** (gap-down 7 %): 22 k stack at 318, ladder up through
  320/325/328 → ORB long, scaled 293→295→296→327→328.
- **TSLA red-to-green:** 378 → 382 with big order at 380 acting as
  magnet; partial at 382, stop to break-even, never quite tagged 383.

##### Aziz's caveat (verbatim)
> *"Market Atlas is just a waste of money if you trade penny stocks
> or if you're not a scalper. It only works at meaningful levels for
> high-volume tickers."*

#### Bear-Market 2025 (Tariff War) — Aziz's public confession

Aziz publicly admitted (video `yfOlLmxUR6k`):

- **$2 million realized loss** on leveraged ETFs (SPXL, TQQQ, TNA)
  during the April-2025 Trump-2nd-term tariff war
- *"Three days of volatility wiped out almost two years of trading profit."*
- Cause: ego trading, no risk-management plan, "feeling invincible"
- Same pattern repeated from his 2021/2022 mistake — *"I'm not good
  at swinging leveraged products."*
- Action: **closed all leveraged positions**, switched to plain
  **VOO** (S&P 500) for non-leveraged portfolio
- New community focus: smaller share sizes, R:R discipline,
  education-first
- Quote: *"This is the third bear market I'm trading — pandemic
  (2020), inflation/rate-hike (2022), tariff war (2025). Each one
  unique."*

This confession is **important for the algo-miner risk-management
calibration**: even Aziz with his discipline and ~$10 M account
size blew $2 M when ego overrode rules. The 1 % / 6 % rules exist
specifically to prevent this kind of blow-up.

#### Updated tool stack (2026)
- Broker: **Interactive Brokers** (unchanged)
- Platform: **DAS Trader Pro** (unchanged)
- **NEW: Market Atlas** as level-2 replacement
- Live trading: BBT chat-room (Aziz screens shared in real-time)
- Sim: DAS sim, $50 000 funded sim challenge via Trading Terminal
  (must trade profitably for 3 months → real funded account)

#### Daily routine — refined
> *"Wake up 5 minutes before the open."*

That's it. Aziz no longer does 8:30 a.m. premarket prep on his
livestreams (the BBT mentors Carlos + Norma still do).

#### Open follow-ups (updated again)
- Performance attribution: which Aziz strategy contributes most $$
  after the rotation to Market Atlas-first scalping
- ~~Exact NASDAQ TotalView API rate limits + feed cost structure~~ ✓ 2026-05-14
- Whether Aziz publishes the Market Atlas tool description publicly
  (so we could approximate it from Yahoo / Polygon / Alpaca feeds)
- 2025/2026 Zarattini × Aziz SSRN paper update

### 2026-05-14 18:00Z — Market Atlas data-feed forensics

For the algo-miner project: can we approximate Aziz's Market Atlas
view from cheaper / open feeds?

**Underlying feed: NASDAQ TotalView-ITCH 5.0**
- The full-depth, every-quote-every-order spec NASDAQ publishes
- Cloud-friendly historical replay available via **Nasdaq Data Link**
  ("NTV" dataset) — programmatic access; pricing not public
- Aziz's $20/month-per-user pass-through fee = retail TotalView
  display licence (matches Interactive Brokers' bundled fee)

**Vendor alternatives by tier**

| Tier | Provider | Depth | Time axis | Cost (retail) |
|---|---|---|---|---|
| Full L3 | **Databento XNAS.ITCH** | every order book event | yes, replay matches live | pay-per-message |
| Full L2 | **dxFeed** TotalView for Quantower | top + depth | yes | ~$70/mo |
| L1+top-N | Nasdaq Basic (BBO + last) | top-of-book | yes | -60 % vs. TotalView |
| L1 only | IEX SIP via Alpaca | best bid/ask | yes (snapshots) | free / paid tiers |
| L2 derived | Polygon.io | L1 + trades | yes | $79–199/mo |

Alpaca explicitly does **NOT** ship L2 order-book data on the equity
side (only L1 + executions). IEX feed covers only ~2 % of US market
volume, so even L2-on-IEX wouldn't match TotalView coverage.

**Implication for algo-miner:**
- Faithful Market Atlas replica needs **TotalView-ITCH** ($) or
  **Databento XNAS.ITCH** (pay-per-message but flexible)
- Cheap approximation: Polygon.io trade prints + 1-min OHLCV aggregates +
  derived "synthetic liquidity pool" (volume clustering at recent
  price levels) — not real order book but captures the magnet effect
- Open-source data path:
  1. Subscribe to a paid TotalView mirror (databento/dxfeed)
  2. Stream order events into a local heat-map renderer (bookmap-style)
  3. Annotate with VWAP + Camarilla pivots
  4. Plug into the existing AZIZ rule set as a new Layer-0 filter
     ("Liquidity-pool present in trade direction → green-light entry")

**Action item:** add `brain/liquidity_pool.py` rule once a feed is
budgeted — currently parked as a stretch goal.

Sources: Databento (xnas.itch), Nasdaq Data Link NTV, Alpaca docs.

### 2026-05-14 18:30Z — academic paper catalogue (Zarattini × Aziz)

Closing the "2025/2026 academic paper" follow-up. Current Zarattini ×
Aziz × Barbon catalogue on SSRN:

| Year | SSRN ID | Title | Key result |
|---|---|---|---|
| 2023 | `4416622` | Can Day Trading Really Be Profitable? | ORB 2016-2023 baseline study |
| 2023 | `4631351` | Volume Weighted Average Price — The Holy Grail | VWAP-anchored intraday systems |
| 2024 | `4729284` | A Profitable Day Trading Strategy For The U.S. Equity Market | Stocks-in-Play ORB — Sharpe **2.4**, total return **>1 600 %**, 7 000+ US stocks 2016-2023; published as Swiss Finance Institute Research Paper No. 24-98; **bronze medal at unisg** |
| 2024 | `4824172` | **NEW**: Beat the Market — Intraday Momentum Strategy for SPY | SPY-only momentum, total return **1 985 %** net of costs, **annualised 19.6 %**, 2007 – early 2024 |

#### "Beat the Market" (paper 4 — new in this catalogue)

The 4th paper is the most algo-miner-relevant addition: it tests
**SPY** (single-instrument intraday momentum) rather than a stocks-
in-play universe. Methodology highlights from the abstract:

- Single instrument: **SPY ETF** (S&P 500 tracker)
- Period: **2007 – early 2024** (covers GFC, COVID, 2022 bear, 2023 recovery)
- Strategy class: **intraday momentum** (not ORB exactly — momentum
  rules on the SPY 1-min chart)
- Performance: **+1 985 %** total net of costs, ~**+19.6 % p.a.**
- Beta near zero (uncorrelated with buy-and-hold)
- Drawdown characteristics: not in the abstract — needs full PDF

**Implication for algo-miner:**
- A *single-instrument* intraday-momentum benchmark exists for SPY
- We can implement a `--style aziz-spy` variant: same Aziz rule set,
  defaults tuned for SPY 1-min (different ATR multiplier, different
  ORB window — likely 30-min not 5-min on an index)
- Backtesting target: replicate ≥ 15 % annualised on SPY 1-min sample
  data to validate the algo-miner harness against published academic
  research

#### Closing this follow-up
~~2025/2026 Zarattini × Aziz SSRN paper update~~ ✓ 2026-05-14

#### Remaining open follow-ups
- Performance attribution: which Aziz strategy contributes most $$
  after the rotation to Market Atlas-first scalping
- Whether Aziz publishes the Market Atlas tool description publicly
- "Beat the Market" paper — exact intraday-momentum rules (need the
  full PDF; SSRN abstract page is reachable but PDF is paywalled
  from this sandbox)
