# Bear Bull Traders Webinar — Camarilla Pivots × Bookmap Order Book
## Speaker: Thor (BBT mentor, *not* Andrew Aziz)
## Source: user-supplied transcript, video ID unknown (likely a private BBT bootcamp)

This is the **third installment of a boot-camp series** by Thor Young, one of
Bear Bull Traders' senior mentors. Speaker references "my Fearless Mentor
Andrew" (= Aziz) and "Andrew … momentum trader" repeatedly to contrast his
own range/order-book approach with Aziz's momentum / ORB approach.

Topic: Camarilla pivot levels combined with Bookmap heat-map order-flow.

---

## Key concepts

### Camarilla pivots — the trader's framework
- Invented by **MB Curton Twig** (Canadian economics student, late 1980s) — NOT Nick Scott
- Used today by **Citadel** and other large market-making firms; ~30-40 % of
  market traffic routes through algos that respect these levels
- "It's manipulated — the house plays with a stacked deck"
- Formula: based on prior-day high, low, close (mathematical standard-deviation
  bands around price)
- Key levels: **R3, R4** above and **S3, S4** below the central pivot range
- Thor uses only the **3s and 4s** (R3/R4/S3/S4); ignores R1/R2/S1/S2 and R5/R6/S5/S6
- DAS Trader Pro has these built in via `pivot` indicator

### Pivot-based bias
| Today vs yesterday pivots | Bias | Treat as |
|---|---|---|
| Slightly higher | Bullish | Prefer long |
| Slightly lower | Bearish | Prefer short |
| Same / cross-cutting | Neutral | Find another ticker |

### Open price confirmation (after the first 1-2 minutes)
| Opens above… | Trade plan |
|---|---|
| R4 | Look for back-test of R4 → long |
| R3 (but below R4) | Sell rallies short |
| S4 (above central) | Buy dips long |
| S3 (below central, above S4) | Short rallies |
| Below S4 | Long after back-test of S4 |

### Inside day vs Outside day
- **Inside day** = today's pivot range is *narrower* than yesterday's
  → expect price to stay inside the range, **zero expectation of breakout**
  → play edges back to middle, middle to other edge
- **Outside day** = today's range is *wider* than yesterday's
  → expect directional move, ideal for **breakouts**
- **Neutral day** = same width → either play pivots as-is or find a better ticker

### Tesla example: opened above R4 on an outside (tight-cam) day → back-tested
R4 → bounced exactly to the cent → went on a breakout. Textbook setup.

### Gray Area concept (critical rule)
- The pivot range **between R3 and S3** is the "gray area" — where price
  finds value and chops
- *"Do NOT initiate trades inside the gray area."* You'll get chopped.
- Trade is valid only at the **edges** (S3/S4 long, R3/R4 short) and at the
  **transitions** between value zones

### Risk-reward via pivot selection
- If you long from **S4**: target R3 → R4 (3-4 R potential)
- If you short from **R4**: target S3 → S4 (3-4 R potential)
- Stop = just outside the level you bought/sold at
- *"Stops at the daily low/high of session create new lows/highs to trigger
  you — that's why those stops get hit before the move runs."*

### Profit factor vs hit rate (math)
- 80 % hit rate × 1 R wins / 1 R losses = barely break-even
- 40 % hit rate × 3 R wins / 1 R losses = great profit factor
- *"Hit rate doesn't tell you if you made money — profit factor does."*

---

## Bookmap (heat-map order book)

### What it shows
- Limit orders = horizontal lines (color intensity = size)
- Market orders = dots (green = buy, red = sell, size = volume)
- Historical view: see WHERE orders sat and how they moved

### Order-book reading rules
- **Bullish book** = thin orders below current price, dense orders above
  → price wants to rise (no headwind, lots of liquidity to absorb sellers)
- **Bearish book** = dense orders below, thin above
  → price wants to fall
- **Balanced book** = transactions all around → no edge, don't trade

### Iceberg orders
- Large players hide size by showing only ~1k at a time (DAS Trader has
  this feature explicitly: "Display: 1000")
- Detect via **absorption** — repeated buying at a level that doesn't move
  the price up = invisible seller absorbing all the buys
- Reverse pattern signals the **fade**: when absorption holds, price
  pulls back rather than breaking through

### Confluence rule (the key tactic)
A trade entry needs **all four** of these to align in a 5-10 minute window:
1. **Pivot level** — at R3/R4/S3/S4 (where the algo decisions cluster)
2. **VPA signal** — volume + price action confirming direction
3. **Order book** — bullish/bearish stack matching trade direction
4. **Iceberg / absorption** at the level being defended

> *"All four simultaneously — that's the re-entry window. It's only open
> 5-10 minutes at a time. Miss it and you wait for the next one."*

### Tesla short example (verbatim re-told)
- Opened above R4 with bullish book
- Back-tested R4, wicked it, then immediately hard-sold off a big seller
- Speaker shorted *into* R4 wick with bearish book stack → bagged the drop
- Andrew Aziz commented in chat: "I don't know how Thor shorted here" —
  because as a momentum trader, Andrew would never short into R4 wick
- Thor: "It's a completely range-based trade — I'm not considering momentum
  like Andrew does."

---

## How this complements Aziz's approach

| Aziz (momentum) | Thor (range / book) |
|---|---|
| Stocks in Play with catalysts | Any ticker with good pivot relationship |
| Trade at VWAP / 9-20 EMA | Trade at R3/R4/S3/S4 |
| Entries at moving averages | Entries at pivot levels with book confirmation |
| Stop at VWAP | Stop just outside the pivot level |
| Target: round numbers, pre-market H/L | Target: opposite pivot in the range |
| Time: first 1.5 h after open | Time: throughout day, especially edges |

**Hybrid** = use Aziz momentum on premarket-catalyst tickers + use Thor's
pivot/book framework on the SPY / QQQ / SPX-future index plays. Aziz himself
adopts the index approach during pandemic-style market-wide volatility.
