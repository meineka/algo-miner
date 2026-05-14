# Andrew Aziz Free Course — Full Curriculum (8 modules)
## Source: user-supplied transcript, English, video ID unknown (likely Aziz's "Free Day Trading Course" series, ~hour+ long)

Speaker: Andrew Aziz directly. Covers his complete teaching arc from
computer setup all the way to building a personal trade book.

---

## Module 1 — System setup & tools

### Computer
- **CPU:** Intel i7 series (current generation)
- **RAM:** 16 GB minimum, 32 GB nice
- **Storage:** SSD
- **GPU:** gaming-class only matters if you want to drive 5+ monitors
- **Internet:** **wired cable**, not Wi-Fi. Low ping > bandwidth.
- **Target latency:** **< 200 ms** (DAS shows it in the bottom status bar)
- Aziz in Vancouver: ~150 ms; New Jersey/NY users: <50 ms (server location)

### Monitors
- Start with **2 monitors**. Don't over-invest before you know it works for you.
- Carlos (BBT senior trader) example: started with 6 monitors, later
  downgraded to fewer-but-larger high-res screens + a Stream Deck for hotkeys

### Brokers
| Broker | Type | When |
|---|---|---|
| Interactive Brokers | Direct-access, commissioned | **Aziz's choice** |
| TD Ameritrade | Direct-access | Good alternative |
| CMEG (Cobra) | Direct-access | Offshore (no PDT rule) |
| Robinhood / commission-free | Order-flow sold to market makers | **Avoid for active trading** |

### Platform
- **DAS Trader Pro** — Aziz's choice, ~$150/month + $15-20 data
- **Cost includes the exchange data feed** in the platform fee
- Pros: best-in-class execution speed, robust direct-access routing
- Cons: Windows-only (Mac users run Parallels), learning curve
- Alternatives: TWS (Interactive Brokers), Thinkorswim (TD)

### Exchange routing
- Routes: `SMRT` (IB smart route), `ARCA`, `EDGX`, `ARCX`
- `EDGX` adds liquidity → ECN rebate (small income offset)

### Simulator rule
- **Minimum 3 months of simulator practice** before going live
- Use the same platform you'll trade live on (DAS sim if you'll trade DAS live)
- Practice psychology too — "sweat on every trade in simulator like it's real"

---

## Module 2 — Seven fundamentals of trading success

1. Education + simulated trading
2. Preparation (pre-market routine, mental + physical)
3. Hard work (smart and consistent, not necessarily long hours — Aziz trades ~1h/day)
4. Patience (poker mantra: Patience, Premium hand, Position)
5. Discipline (sticks across trading, diet, sleep)
6. Mentorship + community
7. Reflection + review (journaling tools: Twitter @JohnK trade-by-trade, BBT chart-log)

> *"Showing up every single day is more important than long hours."*

---

## Module 3 — Watchlist & stocks-in-play

### Scanner criteria (re-stated exactly)
- Gap up or down ≥ **2 %**
- Price range: **$5 – $250**
- ATR: at least **$0.50** intraday range
- Float ≥ **1** (filters out fractional ETFs / shells) — *NOTE: in his
  earlier book he says ≥ 20 M; this newer course uses a softer filter*
- Premarket volume ≥ **100 000 shares**

### Float categories
| Float | Shares | Price band | Aziz's verdict |
|---|---|---|---|
| Low | < 25 M | usually < $10 | **Avoid** — too volatile, deep spread |
| Medium | 25 – 500 M | $10 – $100 | **His favorite** |
| Large / Mega | > 500 M | usually > $20 | Trade with bigger size |

### Catalysts
1. Earnings (most common)
2. FDA approvals (pharma)
3. M&A (e.g. Microsoft × Activision)
4. Contract wins/losses
5. Layoffs, splits, management changes

### Avoid
- Penny stocks (< $5, low-float)
- Block-trade-only premarkets (one giant trade then nothing — usually
  confirmed buyouts trading at the deal price)
- Foreign companies / ADRs (Toyota, Fiat-Chrysler, Chinese names) —
  daily volatility but FX impact distorts price action

### Pre-market routine (clock)
| Time (ET) | Action |
|---|---|
| 08:30 | Scan gappers, read catalysts |
| 08:30 – 09:00 | Identify pre-market levels (high, low, prior-day close) |
| 09:00 – 09:20 | Watch pre-market price action, narrow watchlist |
| 09:15 – 09:25 | Finalize watchlist (max 3–5 names) |
| 09:30 | Market opens — wait 5 minutes (often) |
| 09:30 – 11:00 | Main trading window |
| 11:00 – 15:30 | Mostly skip (Aziz personally does not trade afternoons) |

---

## Module 4 — Support & resistance levels

### Automatic levels (platform provides)
- Previous-day close (PCL) — most important
- Previous-day high / low
- 2-day-ago high / low
- Pre-market high / low
- **Pivot points** (Camarilla via DAS — Aziz uses R3, R4, S3, S4 only)
- Fibonacci (Aziz: "I don't use them")

### Discretionary levels (find yourself)
- Pre-market intraday support/resistance
- Daily-chart moving averages (50 SMA, 200 SMA on daily are very strong)
- Extreme price wicks on the daily — long-tailed candles mark levels
- 52-week high / low
- All-time high / low

### Aziz's level-drawing rules
- Only **horizontal** lines, never trendlines/channels — *"trendlines are
  subjective. If you're in a buy mood you see uptrend; in a sell mood
  you see downtrend. Don't bias yourself."*
- Use levels as **profit targets**, not strategies. Strategy says *go long*;
  levels say *until where*.

---

## Module 5 — Order entry & price action

### Order types
| Type | Behavior | Use case |
|---|---|---|
| Market | Fill now at any price | High-liquidity stocks, urgent fills |
| Limit | Wait at your price | Builds liquidity, ECN rebate possible |
| **Marketable Limit** | Market with a cap (e.g. ask + $0.05) | **Aziz's default** for low-priced or wide-spread stocks |

### Level 2 reading (counter-intuitive rule)
- **Huge bid stack** = bearish sign (price likely to drop)
- **Huge ask stack** = bullish sign (price likely to rise)
- Why: a real desperate seller hits the bid (Market sell), they don't sit
  on the ask. A "no-intention-to-fill" (NITF) big bid is low-balling.
- Only the 1–2 levels closest to current price matter; deeper levels are
  background noise.

### Candlestick interpretation
| Pattern | Body | Wicks | Bias |
|---|---|---|---|
| Bullish marubozu | Big green | None / small | Strong long |
| Bearish marubozu | Big red | None / small | Strong short |
| Hammer | Small green | Long lower wick | Bullish reversal |
| Shooting star | Small green | Long upper wick | Bearish reversal |
| Engulfing (bull) | Green covers prior red entirely | — | **Very strong long reversal** |
| Engulfing (bear) | Red covers prior green entirely | — | **Very strong short reversal** |
| Higher high + higher low | Sequence | — | Uptrend (5-min) |
| Lower high + lower low | Sequence | — | Downtrend (5-min) |

> *"5-min engulfing crack at the open is a strategy by itself — I trade it
> almost every time I see one."*

### Trade-management rules (verbatim)
1. After first partial → move stop to **break-even**
2. *"Never go red on a stock you booked profit on."*
3. If the pattern changes (higher-low becomes lower-low or vice versa)
   *before* you hit your original stop, **get out at break-even** —
   don't wait for the original stop
4. *"Bullish candles are not shorts even if they reject a level."*
5. Reduce size on high-volatility, low-priced, low-float, or wide-spread tickers
6. Increase size only when *all criteria align* (gap, volume, level, pattern)

---

## Module 6 — Strategies (deeper detail)

### Trend strategies (price-direction trades)
- Opening Range Breakout (ORB) — 1-min, 2-min, 5-min, 15-min, 30-min, 60-min
- Bull Flag / Bear Flag — works best on low-price low-float stocks
- ABCD pattern — same shape as flag, used on higher-price stocks
- Break of High of Day

### Counter-trend strategies (reversal trades)
- 9 / 20 Reversal ("920 trade") — 2-min chart only, between 10:00 – 10:30
- Parabolic reversal
- Double bottom
- False breakout

### Time-of-day matrix
| Window | Best strategies |
|---|---|
| 09:30 – 10:00 | ORB, Fallen Angel, breakaway 5/30 mountain pass |
| 10:00 – 11:00 | 920 reversal, parabolic reversal, double bottom |
| 11:00 – 15:30 | Aziz mostly skips — light volume, low momentum |
| Near close | Less momentum, fewer scalp setups |

### 920 trade — verbatim recipe
1. Stock has been **strongly above VWAP** for the first 30–45 minutes
2. Use **2-minute chart only** (not 1-min, not 5-min)
3. Wait for pullback to the **20 EMA** between **10:00 – 10:30**
4. Long with **stop just below 20 EMA**
5. First partial = touch of **9 EMA**
6. Second partial = **break of high of day**
7. Add on additional pullback to 9 EMA if trend continues

---

## Module 7 — Risk management

### Position-size formula
> *Max risk dollars = Account × 1 %* (or 0.5 % for conservative, 2 % aggressive)
> *Position size in shares = Max risk dollars / Stop distance in dollars*

Example: $40 000 account, 1 % rule, $50 stock, $0.40 stop → 1 000 shares.

### Risk-reward gate
- **Minimum 2:1** before entering. Don't take 1:1 trades.
- If chasing the stock pushes R:R below 1:1 → skip the trade.

### The "Hawk day" trap (Aziz's term for "tilt day")
Signs you're on a Hawk day:
- Agitated, too much caffeine, looking at P&L every second
- Revenge trading after a loss
- Adding to losing positions ("averaging down")
- Many tickers, many orders, no plan

Treatment: **Stop. Walk away. Switch to simulator. Set a max-daily-loss
broker-side lock-out.**

### The 1 % rule
*"Never lose more than 1 % of your account on a single trade."*
Protects from the **shark bite**.

### The 6 % rule
*"If you lose 6 % of your account in the last 30 days, switch to simulator
for 2 weeks before going live again."*
Protects from the **piranha bite** (death by 1 000 small losses).

### Account-size growth curve
Aziz's own equity curve (his memory): "Couple of hundred dollars per day
in 2015–2017, then slowly into thousands as the account grew. Don't look
at P&L for the first couple of months — focus on emotions and process."

---

## Module 8 — Psychology & trade book

### Emotions in trading (simulator vs live)
- *"Simulator trading is easy — there's no real risk. Real money is like
  walking the same plank, but on top of a skyscraper instead of on the ground.
  Same skill, completely different psychology."*

### The 10 lessons (Aziz's curriculum)
1. Develop confidence
2. Know your strengths and weaknesses (e.g. Aziz isn't an options trader)
3. Be open to change and learning
4. Develop self-awareness
5. Manage stress (meditation, mindfulness)
6. Know when to take a break
7. Build a routine (in life and trading)
8. Identify your emotions in real time
9. Control your environment (music, caffeine, sleep)
10. Keep going — early doubt is universal

### The Trade Book ("Handbook" / "Fachbuch")
Every successful trader builds a personal printed trade book. Sections:
1. Stock selection criteria
2. Time-of-day windows
3. Trade identification (chart pattern + indicators)
4. Trade execution (entry trigger, share size, stop)
5. Trade management (partials, break-even, exits)
6. Psychology notes (your common mistakes, how to counter them)
7. Worked examples (5 – 10 historical trades)

> *"By the time you've built it, you don't need to read it anymore.
> It lives in your muscle memory."*

### Sample trade books available
At `bearbulltraders.com/gifts` and the BBT chat-room Downloads folder:
- ABCD trade book
- Mountain Pass trade book
- Others by senior community traders (named like "NyQuil" after their creator)

### Peer support
- BBT chat-room, daily live trade alongside Aziz (you see his screen)
- Thursday mentorship sessions
- BBT-Women private slack channel
- Encouraged: form WhatsApp / Discord groups with a few like-minded traders

### Aziz's parting advice
- Start small. Don't worry about commissions or fees in month 1.
- Scared money is lost money — don't trade your life savings.
- Reduce share size during losing streaks; never double down.
- Ignore daily $-target goals; trade quality setups, average it out monthly.
- **Believe in compounding** — 1 %/day for 9 months is life-changing.
