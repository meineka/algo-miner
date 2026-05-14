//+------------------------------------------------------------------+
//|                                              Aziz_NQ.mq5     |
//|                                                          meineka |
//|                       https://github.com/meineka/algo-miner      |
//+------------------------------------------------------------------+
//
//  ANDREW-AZIZ HYBRID EA FOR NQ (NASDAQ-100 CFD)
//  =================================================
//  Version 3.0 — second audit pass; bug-fixes over v2.0:
//    • VWAP-reclaim now actually triggers (streak captured BEFORE cross).
//    • OnNewBar pattern — signal evaluated once per M1 close, not every tick.
//    • Auto-flat before session close (optional).
//    • Spread filter to skip wide-spread ticks.
//    • Diagnostic counters increment per *decision*, not per tick.
//    • Magic number is `ulong` consistently.
//
//  Entry routes  : (1) Opening Range Breakout + VWAP filter + 9/20 EMA trend
//                  (2) VWAP reclaim/loss after N opposite-side closes
//  Exits         : SL = ATR × mult; 50 % partial at +1R → SL → break-even;
//                  remainder rides to +2R (broker-side TP).
//                  Optional auto-flat at session-close − N min.
//  Risk          : 1 % per trade; 2 % daily loss; 3-strike cooldown;
//                  6 % drawdown kill; max-trades-per-day cap; spread guard.
//  Target broker : GoMarkets NQ / US100 / USTEC CFD on MT5.
//  Backtest      : Strategy Tester, "Every tick based on real ticks" (mode 4).
//                  Recommended period: 2024-04-01 → today.
//
//+------------------------------------------------------------------+

#property copyright   "meineka"
#property link        "https://github.com/meineka/algo-miner"
#property version     "3.00"
#property strict
#property description "Aziz hybrid EA for NQ — ORB + VWAP reclaim + 9/20 EMA trend"
#property description "Audited v3: VWAP-reclaim fix, OnNewBar gate, spread filter, auto-flat"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

CTrade        trade;
CPositionInfo position;

//============================================================================
// INPUTS
//============================================================================

input group "── Asset & Session (server time, see README) ──"
input string Inp_SymbolAlias       = "";   // empty → use chart symbol; e.g. "NQ" / "US100" / "USTEC"
input int    Inp_SessionOpenHour   = 13;   // NY 09:30 ET = 13:30 UTC (DST). GoMarkets server time = UTC+2/+3 ⇒ adjust to 15:30 (DST) / 16:30 (winter). See README.
input int    Inp_SessionOpenMin    = 30;
input int    Inp_SessionCloseHour  = 20;
input int    Inp_SessionCloseMin   = 0;
input int    Inp_BlackoutCloseMin  = 30;
input int    Inp_ORB_WindowMinutes = 15;
input int    Inp_MaxTradesPerDay   = 4;
input bool   Inp_AutoFlatOnClose   = true;   // close all positions N min before session close
input int    Inp_AutoFlatMin       = 5;

input group "── Entry routes ──"
input bool   Inp_UseORB            = true;
input bool   Inp_UseVWAPReclaim    = true;
input int    Inp_VWAPConfirmBars   = 2;      // streak of opposite-side closes before the cross

input group "── Filters ──"
input bool   Inp_UseVWAPFilter      = true;
input bool   Inp_UseEMATrendFilter  = true;
input int    Inp_EMA_Fast           = 9;
input int    Inp_EMA_Slow           = 20;
input double Inp_BreakoutVolMult    = 1.3;
input int    Inp_MaxSpreadPoints    = 50;    // 0 disables; in MT5 points

input group "── Risk management (Aziz house rules) ──"
input double Inp_RiskPerTradePct    = 1.0;
input double Inp_MaxDailyLossPct    = 2.0;
input int    Inp_MaxConsecutiveLoss = 3;
input int    Inp_CooldownBars       = 5;
input double Inp_MaxDrawdownPct     = 6.0;
input int    Inp_ATR_Period         = 14;
input double Inp_ATR_StopMult       = 1.5;
input double Inp_TP1_R_Multiple     = 1.0;
input double Inp_TP2_R_Multiple     = 2.0;
input double Inp_Partial1Pct        = 50.0;

input group "── Execution ──"
input ulong  Inp_MagicNumber        = 20260514;
input ulong  Inp_DeviationPoints    = 20;
input string Inp_Comment            = "AZIZ_NQ";
input bool   Inp_Verbose            = false;

//============================================================================
// STATE
//============================================================================

int      g_hEMA_fast = INVALID_HANDLE;
int      g_hEMA_slow = INVALID_HANDLE;
int      g_hATR      = INVALID_HANDLE;

// Session-scoped
datetime g_session_open_time   = 0;
datetime g_session_close_time  = 0;
datetime g_session_flat_time   = 0;
datetime g_orb_done_time       = 0;
double   g_orb_high            = -DBL_MAX;
double   g_orb_low             =  DBL_MAX;
double   g_orb_volume_avg      = 0.0;
bool     g_orb_finalised       = false;
bool     g_orb_traded_long     = false;
bool     g_orb_traded_short    = false;
bool     g_vwap_reclaim_done   = false;
int      g_trades_today        = 0;

// Running session VWAP — see VWAP_RECLAIM_DESIGN note below for state semantics.
double   g_vwap_cum_pv         = 0.0;
double   g_vwap_cum_vol        = 0.0;
datetime g_last_vwap_bar_time  = 0;
//  Captured BEFORE the latest bar is processed — these tell us
//  "how many bars in a row was the asset below VWAP up to and
//   including the *previous* bar".
int      g_streak_below_at_prev = 0;
int      g_streak_above_at_prev = 0;
//  Live counters, updated AFTER each bar.
int      g_streak_below_cur    = 0;
int      g_streak_above_cur    = 0;

// OnNewBar gate
datetime g_last_processed_bar  = 0;

// Risk / circuit-breaker
datetime g_today_date          = 0;
double   g_today_start_equity  = 0.0;
double   g_today_realized_pnl  = 0.0;
int      g_consecutive_losses  = 0;
int      g_bars_since_trade    = 9999;
double   g_peak_equity         = 0.0;
bool     g_halted_for_day      = false;
bool     g_halted_for_dd       = false;

// Open-position tracker (single position, magic-filtered)
double   g_open_entry_price    = 0.0;
double   g_open_initial_sl     = 0.0;
double   g_open_tp1_price      = 0.0;
double   g_open_tp2_price      = 0.0;
double   g_open_initial_lots   = 0.0;
int      g_open_direction      = 0;
bool     g_open_tp1_filled     = false;

// Backtest statistics — incremented per decision/event
int      g_stat_trades_opened   = 0;
int      g_stat_trades_won      = 0;
int      g_stat_trades_lost     = 0;
double   g_stat_gross_win       = 0.0;
double   g_stat_gross_loss      = 0.0;
int      g_stat_partial_fills   = 0;
int      g_stat_orb_signals     = 0;
int      g_stat_vwap_signals    = 0;
int      g_stat_blocked_daystop = 0;   // count of bars where new-trade would have been issued but day-stop kicked in
int      g_stat_blocked_dd      = 0;
int      g_stat_blocked_cooldown= 0;
int      g_stat_blocked_spread  = 0;
int      g_stat_autoflats       = 0;

string   g_symbol              = "";

//============================================================================
// LIFECYCLE
//============================================================================

int OnInit()
{
   g_symbol = (StringLen(Inp_SymbolAlias) > 0) ? Inp_SymbolAlias : _Symbol;
   if(!SymbolSelect(g_symbol, true))
   { PrintFormat("[AZIZ_NQ] Symbol '%s' not available — abort.", g_symbol); return INIT_FAILED; }

   if(Inp_EMA_Fast >= Inp_EMA_Slow)
   { Print("[AZIZ_NQ] EMA_Fast must be < EMA_Slow"); return INIT_PARAMETERS_INCORRECT; }
   if(Inp_ORB_WindowMinutes < 1)
   { Print("[AZIZ_NQ] ORB_WindowMinutes must be >= 1"); return INIT_PARAMETERS_INCORRECT; }
   if(Inp_SessionCloseHour * 60 + Inp_SessionCloseMin <=
      Inp_SessionOpenHour  * 60 + Inp_SessionOpenMin)
   { Print("[AZIZ_NQ] Session close must be after session open"); return INIT_PARAMETERS_INCORRECT; }
   if(!Inp_UseORB && !Inp_UseVWAPReclaim)
   { Print("[AZIZ_NQ] Enable at least one entry route (ORB or VWAP reclaim)"); return INIT_PARAMETERS_INCORRECT; }
   if(Inp_VWAPConfirmBars < 1)
   { Print("[AZIZ_NQ] VWAPConfirmBars must be >= 1"); return INIT_PARAMETERS_INCORRECT; }

   g_hEMA_fast = iMA(g_symbol, PERIOD_M1, Inp_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMA_slow = iMA(g_symbol, PERIOD_M1, Inp_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   g_hATR      = iATR(g_symbol, PERIOD_M1, Inp_ATR_Period);
   if(g_hEMA_fast == INVALID_HANDLE || g_hEMA_slow == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   { Print("[AZIZ_NQ] indicator handle creation failed — abort."); return INIT_FAILED; }

   trade.SetExpertMagicNumber(Inp_MagicNumber);
   trade.SetDeviationInPoints(Inp_DeviationPoints);
   trade.SetTypeFillingBySymbol(g_symbol);

   g_peak_equity         = AccountInfoDouble(ACCOUNT_EQUITY);
   g_today_start_equity  = g_peak_equity;
   RolloverDay(TodayDate());

   PrintFormat("[AZIZ_NQ] v3 init OK on %s | risk=%.2f%% | day-stop=%.2f%% | DD=%.2f%% | session %02d:%02d–%02d:%02d UTC",
               g_symbol, Inp_RiskPerTradePct, Inp_MaxDailyLossPct, Inp_MaxDrawdownPct,
               Inp_SessionOpenHour, Inp_SessionOpenMin, Inp_SessionCloseHour, Inp_SessionCloseMin);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hEMA_fast != INVALID_HANDLE) IndicatorRelease(g_hEMA_fast);
   if(g_hEMA_slow != INVALID_HANDLE) IndicatorRelease(g_hEMA_slow);
   if(g_hATR      != INVALID_HANDLE) IndicatorRelease(g_hATR);
}

double OnTester()
{
   PrintBacktestSummary();
   return (g_stat_gross_loss > 0) ? (g_stat_gross_win / g_stat_gross_loss) : 0.0;
}

//============================================================================
// TICK LOOP — minimal work per tick; signal decisions only on new M1 close
//============================================================================

void OnTick()
{
   datetime today = TodayDate();
   if(today != g_today_date) RolloverDay(today);

   // Equity / DD tracking (every tick, very cheap)
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peak_equity) g_peak_equity = eq;
   if(!g_halted_for_dd && g_peak_equity > 0)
   {
      double dd_pct = 100.0 * (g_peak_equity - eq) / g_peak_equity;
      if(dd_pct >= Inp_MaxDrawdownPct)
      {
         PrintFormat("[AZIZ_NQ] DD-kill: %.2f%% > %.2f%%. EA halted permanently.", dd_pct, Inp_MaxDrawdownPct);
         g_halted_for_dd = true;
         CloseAllPositions();
      }
   }
   if(g_halted_for_dd) return;

   if(!g_halted_for_day && g_today_start_equity > 0)
   {
      double day_loss_pct = 100.0 * (-g_today_realized_pnl) / g_today_start_equity;
      if(day_loss_pct >= Inp_MaxDailyLossPct)
      {
         PrintFormat("[AZIZ_NQ] daily-loss circuit-breaker: %.2f%% >= %.2f%%. Paused until next session.",
                     day_loss_pct, Inp_MaxDailyLossPct);
         g_halted_for_day = true;
         CloseAllPositions();
      }
   }

   // Auto-flat near session close
   if(Inp_AutoFlatOnClose && g_session_flat_time > 0 && TimeCurrent() >= g_session_flat_time && HasOpenPosition())
   {
      PrintFormat("[AZIZ_NQ] auto-flat before session close");
      CloseAllPositions();
      g_stat_autoflats++;
   }

   // Manage open positions every tick (TP1 partial check)
   if(HasOpenPosition()) { ManageOpenPosition(); g_bars_since_trade = 0; return; }

   // OnNewBar gate — only re-evaluate signal once per new M1 close
   if(!NewM1BarClosed()) return;

   if(g_halted_for_day)                                  { g_stat_blocked_daystop++; return; }
   if(g_consecutive_losses >= Inp_MaxConsecutiveLoss)    { g_stat_blocked_cooldown++; return; }
   if(g_bars_since_trade < Inp_CooldownBars)             { g_bars_since_trade++; return; }
   if(g_trades_today >= Inp_MaxTradesPerDay)             return;
   if(!IsInTradingWindow())                              return;
   if(!SpreadWithinLimit())                              { g_stat_blocked_spread++; return; }

   UpdateSessionVWAP();
   if(!g_orb_finalised) MaybeFinaliseORB();

   int signal = ComputeSignal();
   if(signal != 0) OpenTrade(signal);
}

//============================================================================
// SESSION & DAILY ROLLOVER
//============================================================================

datetime TodayDate()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   return StructToTime(dt);
}

void RolloverDay(datetime new_day)
{
   g_today_date          = new_day;
   g_today_start_equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   g_today_realized_pnl  = 0.0;
   g_halted_for_day      = false;
   g_trades_today        = 0;

   g_session_open_time   = ComposeWithTime(new_day, Inp_SessionOpenHour,  Inp_SessionOpenMin);
   g_session_close_time  = ComposeWithTime(new_day, Inp_SessionCloseHour, Inp_SessionCloseMin);
   g_session_flat_time   = g_session_close_time - Inp_AutoFlatMin * 60;
   g_orb_done_time       = g_session_open_time + Inp_ORB_WindowMinutes * 60;
   g_orb_high            = -DBL_MAX;
   g_orb_low             =  DBL_MAX;
   g_orb_volume_avg      = 0.0;
   g_orb_finalised       = false;
   g_orb_traded_long     = false;
   g_orb_traded_short    = false;
   g_vwap_reclaim_done   = false;

   g_vwap_cum_pv         = 0.0;
   g_vwap_cum_vol        = 0.0;
   g_last_vwap_bar_time  = 0;
   g_streak_below_at_prev = 0;
   g_streak_above_at_prev = 0;
   g_streak_below_cur    = 0;
   g_streak_above_cur    = 0;
}

datetime ComposeWithTime(datetime day, int hour, int minute)
{
   MqlDateTime dt;
   TimeToStruct(day, dt);
   dt.hour = hour; dt.min = minute; dt.sec = 0;
   return StructToTime(dt);
}

bool IsInTradingWindow()
{
   datetime now = TimeCurrent();
   if(now < g_orb_done_time)                                     return false;
   if(now > g_session_close_time - Inp_BlackoutCloseMin * 60)    return false;
   return now <= g_session_close_time;
}

bool NewM1BarClosed()
{
   datetime t[1];
   if(CopyTime(g_symbol, PERIOD_M1, 1, 1, t) <= 0) return false;
   if(t[0] == g_last_processed_bar) return false;
   g_last_processed_bar = t[0];
   return true;
}

bool SpreadWithinLimit()
{
   if(Inp_MaxSpreadPoints <= 0) return true;
   long spread = SymbolInfoInteger(g_symbol, SYMBOL_SPREAD);
   return (spread <= Inp_MaxSpreadPoints);
}

//============================================================================
// OPENING RANGE
//============================================================================

void MaybeFinaliseORB()
{
   datetime now = TimeCurrent();
   if(now < g_orb_done_time) return;

   int n = Inp_ORB_WindowMinutes;
   double highs[]; double lows[]; long vols[];
   if(CopyHigh      (g_symbol, PERIOD_M1, g_session_open_time, n, highs) <= 0) return;
   if(CopyLow       (g_symbol, PERIOD_M1, g_session_open_time, n, lows)  <= 0) return;
   if(CopyTickVolume(g_symbol, PERIOD_M1, g_session_open_time, n, vols)  <= 0) return;

   double hh = -DBL_MAX, ll = DBL_MAX, vsum = 0;
   int count = ArraySize(highs);
   for(int i = 0; i < count; i++)
   {
      if(highs[i] > hh) hh = highs[i];
      if(lows[i]  < ll) ll = lows[i];
      vsum += (double)vols[i];
   }
   if(count == 0 || hh == -DBL_MAX || ll == DBL_MAX) return;

   g_orb_high       = hh;
   g_orb_low        = ll;
   g_orb_volume_avg = vsum / count;
   g_orb_finalised  = true;

   if(Inp_Verbose)
      PrintFormat("[AZIZ_NQ] ORB %s HI=%.2f LO=%.2f avgVol=%.0f",
                  TimeToString(now, TIME_DATE|TIME_MINUTES), g_orb_high, g_orb_low, g_orb_volume_avg);
}

//============================================================================
// SESSION VWAP — fixed semantics
//   g_streak_below_at_prev / g_streak_above_at_prev capture the streak
//   AT THE END of the bar BEFORE the most-recent fully-closed bar.
//   This is what the VWAP-reclaim check needs.
//============================================================================

void UpdateSessionVWAP()
{
   datetime now = TimeCurrent();
   if(now < g_session_open_time) return;

   datetime from = (g_last_vwap_bar_time == 0) ? g_session_open_time : g_last_vwap_bar_time + 60;
   if(from >= now) return;

   int n_request = (int)((now - from) / 60);
   if(n_request <= 0) return;

   double highs[]; double lows[]; double closes[]; long vols[]; datetime times[];
   if(CopyHigh      (g_symbol, PERIOD_M1, from, n_request, highs)  <= 0) return;
   if(CopyLow       (g_symbol, PERIOD_M1, from, n_request, lows)   <= 0) return;
   if(CopyClose     (g_symbol, PERIOD_M1, from, n_request, closes) <= 0) return;
   if(CopyTickVolume(g_symbol, PERIOD_M1, from, n_request, vols)   <= 0) return;
   if(CopyTime      (g_symbol, PERIOD_M1, from, n_request, times)  <= 0) return;

   for(int i = 0; i < ArraySize(closes); i++)
   {
      // 1. Snapshot streak BEFORE this bar is processed.
      g_streak_below_at_prev = g_streak_below_cur;
      g_streak_above_at_prev = g_streak_above_cur;

      // 2. Update cumulative VWAP.
      double typ = (highs[i] + lows[i] + closes[i]) / 3.0;
      double v   = (double)vols[i];
      g_vwap_cum_pv  += typ * v;
      g_vwap_cum_vol += v;

      double vwap_now = (g_vwap_cum_vol > 0) ? (g_vwap_cum_pv / g_vwap_cum_vol) : 0.0;

      // 3. Update current streak based on this bar.
      if(closes[i] > vwap_now)      { g_streak_above_cur++; g_streak_below_cur = 0; }
      else if(closes[i] < vwap_now) { g_streak_below_cur++; g_streak_above_cur = 0; }

      g_last_vwap_bar_time = times[i];
   }
}

double CurrentVWAP()
{
   if(g_vwap_cum_vol <= 0.0) return 0.0;
   return g_vwap_cum_pv / g_vwap_cum_vol;
}

//============================================================================
// SIGNAL — ORB + VWAP-reclaim
//============================================================================

int ComputeSignal()
{
   MqlRates rates[];
   if(CopyRates(g_symbol, PERIOD_M1, 1, 1, rates) <= 0) return 0;
   double last_open  = rates[0].open;
   double last_close = rates[0].close;
   double last_vol   = (double)rates[0].tick_volume;

   double ema_fast_buf[1]; double ema_slow_buf[1];
   if(CopyBuffer(g_hEMA_fast, 0, 1, 1, ema_fast_buf) <= 0) return 0;
   if(CopyBuffer(g_hEMA_slow, 0, 1, 1, ema_slow_buf) <= 0) return 0;
   double ema_fast = ema_fast_buf[0];
   double ema_slow = ema_slow_buf[0];

   double vwap = CurrentVWAP();
   if((Inp_UseVWAPFilter || Inp_UseVWAPReclaim) && vwap == 0.0) return 0;

   bool vol_break_ok = last_vol > Inp_BreakoutVolMult * MathMax(g_orb_volume_avg, 1.0);
   bool bull_bar     = last_close > last_open;
   bool bear_bar     = last_close < last_open;

   // ──── Route 1: ORB breakout ──────────────────────────────────────────
   if(Inp_UseORB && g_orb_finalised)
   {
      if((last_close > g_orb_high) && vol_break_ok && !g_orb_traded_long)
      {
         bool vwap_ok = !Inp_UseVWAPFilter || (last_close > vwap);
         bool ema_ok  = !Inp_UseEMATrendFilter || (ema_fast > ema_slow);
         if(vwap_ok && ema_ok) { g_stat_orb_signals++; return +1; }
      }
      if((last_close < g_orb_low) && vol_break_ok && !g_orb_traded_short)
      {
         bool vwap_ok = !Inp_UseVWAPFilter || (last_close < vwap);
         bool ema_ok  = !Inp_UseEMATrendFilter || (ema_fast < ema_slow);
         if(vwap_ok && ema_ok) { g_stat_orb_signals++; return -1; }
      }
   }

   // ──── Route 2: VWAP reclaim / loss ───────────────────────────────────
   // A reclaim is:
   //    streak_below_at_prev >= ConfirmBars  (bars before THIS bar were below VWAP)
   //    AND THIS bar closed above VWAP        (g_streak_above_cur == 1 means just crossed)
   //    AND THIS bar is bullish               (bull_bar)
   if(Inp_UseVWAPReclaim && !g_vwap_reclaim_done)
   {
      bool reclaim_up = (g_streak_below_at_prev >= Inp_VWAPConfirmBars) &&
                        (g_streak_above_cur == 1) && bull_bar;
      bool loss_down  = (g_streak_above_at_prev >= Inp_VWAPConfirmBars) &&
                        (g_streak_below_cur == 1) && bear_bar;

      if(reclaim_up)
      {
         bool ema_ok = !Inp_UseEMATrendFilter || (ema_fast > ema_slow);
         if(ema_ok) { g_stat_vwap_signals++; g_vwap_reclaim_done = true; return +1; }
      }
      if(loss_down)
      {
         bool ema_ok = !Inp_UseEMATrendFilter || (ema_fast < ema_slow);
         if(ema_ok) { g_stat_vwap_signals++; g_vwap_reclaim_done = true; return -1; }
      }
   }
   return 0;
}

//============================================================================
// POSITION OPEN
//============================================================================

void OpenTrade(int direction)
{
   double ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double price = (direction > 0) ? ask : bid;

   double atr_buf[1];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr_buf) <= 0) return;
   double atr = atr_buf[0];
   if(atr <= 0.0)
   { if(Inp_Verbose) Print("[AZIZ_NQ] ATR<=0, skipping trade"); return; }

   double stop_dist = atr * Inp_ATR_StopMult;
   double sl_price  = (direction > 0) ? (price - stop_dist) : (price + stop_dist);
   double tp1_price = (direction > 0) ? (price + stop_dist * Inp_TP1_R_Multiple) : (price - stop_dist * Inp_TP1_R_Multiple);
   double tp2_price = (direction > 0) ? (price + stop_dist * Inp_TP2_R_Multiple) : (price - stop_dist * Inp_TP2_R_Multiple);

   int digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
   sl_price  = NormalizeDouble(sl_price,  digits);
   tp1_price = NormalizeDouble(tp1_price, digits);
   tp2_price = NormalizeDouble(tp2_price, digits);

   double lots = CalculateLotSize(stop_dist);
   if(lots <= 0)
   { if(Inp_Verbose) Print("[AZIZ_NQ] computed lot size = 0, skipping"); return; }

   bool ok = (direction > 0)
             ? trade.Buy(lots,  g_symbol, price, sl_price, tp2_price, Inp_Comment)
             : trade.Sell(lots, g_symbol, price, sl_price, tp2_price, Inp_Comment);
   if(!ok)
   {
      PrintFormat("[AZIZ_NQ] order failed: code=%d retcode=%d %s",
                  GetLastError(), trade.ResultRetcode(), trade.ResultRetcodeDescription());
      return;
   }

   g_open_entry_price  = price;
   g_open_initial_sl   = sl_price;
   g_open_tp1_price    = tp1_price;
   g_open_tp2_price    = tp2_price;
   g_open_initial_lots = lots;
   g_open_direction    = direction;
   g_open_tp1_filled   = false;

   if(direction > 0) g_orb_traded_long  = true; else g_orb_traded_short = true;
   g_trades_today++;
   g_bars_since_trade = 0;
   g_stat_trades_opened++;

   PrintFormat("[AZIZ_NQ] %s @ %.2f  SL=%.2f  TP1=%.2f  TP2=%.2f  lots=%.2f  ATR=%.2f  spread=%dpt",
               (direction > 0) ? "LONG" : "SHORT", price, sl_price, tp1_price, tp2_price, lots, atr,
               (int)SymbolInfoInteger(g_symbol, SYMBOL_SPREAD));
}

double CalculateLotSize(double stop_distance)
{
   double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money = equity * (Inp_RiskPerTradePct / 100.0);

   double tick_size  = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0 || tick_value <= 0) return 0.0;

   double loss_per_lot = (stop_distance / tick_size) * tick_value;
   if(loss_per_lot <= 0) return 0.0;

   double lots = risk_money / loss_per_lot;

   double min_lot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;

   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, 2);
   if(lots < min_lot) return 0.0;
   if(lots > max_lot) lots = max_lot;
   return lots;
}

//============================================================================
// POSITION MANAGEMENT
//============================================================================

bool SelectOwnPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!position.SelectByIndex(i)) continue;
      if(position.Symbol() != g_symbol) continue;
      if(position.Magic()  != (long)Inp_MagicNumber) continue;
      return true;
   }
   return false;
}

bool HasOpenPosition() { return SelectOwnPosition(); }

void ManageOpenPosition()
{
   if(!SelectOwnPosition()) return;
   if(g_open_tp1_filled) return;

   ulong  ticket = position.Ticket();
   double price  = (g_open_direction > 0)
                   ? SymbolInfoDouble(g_symbol, SYMBOL_BID)
                   : SymbolInfoDouble(g_symbol, SYMBOL_ASK);

   bool tp1_reached = (g_open_direction > 0 && price >= g_open_tp1_price)
                   || (g_open_direction < 0 && price <= g_open_tp1_price);
   if(!tp1_reached) return;

   double remaining = position.Volume();
   double close_lots = g_open_initial_lots * (Inp_Partial1Pct / 100.0);
   double step       = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;
   close_lots = NormalizeDouble(MathFloor(close_lots / step) * step, 2);
   double min_lot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   if(close_lots < min_lot || close_lots >= remaining) return;

   if(!trade.PositionClosePartial(ticket, close_lots))
   {
      if(Inp_Verbose) PrintFormat("[AZIZ_NQ] partial close failed code=%d", trade.ResultRetcode());
      return;
   }
   g_open_tp1_filled = true;
   g_stat_partial_fills++;

   // Re-select after partial.
   if(SelectOwnPosition())
   {
      int digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
      double be   = NormalizeDouble(g_open_entry_price, digits);
      double tp2  = NormalizeDouble(g_open_tp2_price,   digits);
      if(!trade.PositionModify(position.Ticket(), be, tp2))
         if(Inp_Verbose) PrintFormat("[AZIZ_NQ] BE modify failed code=%d", trade.ResultRetcode());
   }
   if(Inp_Verbose) PrintFormat("[AZIZ_NQ] TP1 partial %.2f lots @ %.2f, stop→BE", close_lots, price);
}

void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!position.SelectByIndex(i)) continue;
      if(position.Symbol() != g_symbol) continue;
      if(position.Magic()  != (long)Inp_MagicNumber) continue;
      trade.PositionClose(position.Ticket());
   }
}

//============================================================================
// REALIZED P&L TRACKING
//============================================================================

void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest&     request,
                        const MqlTradeResult&      result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   ulong deal_ticket = trans.deal;
   if(deal_ticket == 0) return;
   if(!HistoryDealSelect(deal_ticket)) return;

   long magic = (long)HistoryDealGetInteger(deal_ticket, DEAL_MAGIC);
   if(magic != (long)Inp_MagicNumber) return;

   long entry = (long)HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_INOUT) return;

   double pnl = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT)
              + HistoryDealGetDouble(deal_ticket, DEAL_SWAP)
              + HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
   g_today_realized_pnl += pnl;

   if(pnl > 0)      { g_consecutive_losses = 0;  g_stat_trades_won++;  g_stat_gross_win  += pnl; }
   else if(pnl < 0) { g_consecutive_losses++;    g_stat_trades_lost++; g_stat_gross_loss += -pnl; }

   if(!HasOpenPosition())
   {
      g_open_tp1_filled = false;
      g_open_direction  = 0;
   }
   if(Inp_Verbose) PrintFormat("[AZIZ_NQ] deal pnl=%.2f day_pnl=%.2f consec_loss=%d",
                                pnl, g_today_realized_pnl, g_consecutive_losses);
}

//============================================================================
// REPORTING
//============================================================================

void PrintBacktestSummary()
{
   int    total      = g_stat_trades_opened;
   double net        = g_stat_gross_win - g_stat_gross_loss;
   double winrate    = (total > 0) ? 100.0 * g_stat_trades_won / total : 0.0;
   double pf         = (g_stat_gross_loss > 0) ? g_stat_gross_win / g_stat_gross_loss : 0.0;
   double avg_win    = (g_stat_trades_won  > 0) ? g_stat_gross_win  / g_stat_trades_won  : 0.0;
   double avg_loss   = (g_stat_trades_lost > 0) ? g_stat_gross_loss / g_stat_trades_lost : 0.0;
   double r_expect   = (avg_loss > 0) ? (avg_win / avg_loss) : 0.0;

   Print("══════════════════════════════════════════════════════════════════");
   Print(" Aziz NQ EA — backtest summary");
   Print("══════════════════════════════════════════════════════════════════");
   PrintFormat(" Symbol                : %s", g_symbol);
   PrintFormat(" Trades opened         : %d  (won %d / lost %d)", total, g_stat_trades_won, g_stat_trades_lost);
   PrintFormat(" Partial fills (TP1)   : %d", g_stat_partial_fills);
   PrintFormat(" Win rate              : %.2f%%", winrate);
   PrintFormat(" Net P&L               : %+.2f", net);
   PrintFormat(" Profit factor         : %.2f", pf);
   PrintFormat(" Avg win / avg loss    : %.2f / %.2f  (R≈%.2f)", avg_win, avg_loss, r_expect);
   PrintFormat(" Signals  ORB / VWAP   : %d / %d", g_stat_orb_signals, g_stat_vwap_signals);
   PrintFormat(" Auto-flats (close)    : %d", g_stat_autoflats);
   PrintFormat(" Blocked  day-stop     : %d", g_stat_blocked_daystop);
   PrintFormat(" Blocked  DD-kill      : %d", g_stat_blocked_dd);
   PrintFormat(" Blocked  cooldown     : %d", g_stat_blocked_cooldown);
   PrintFormat(" Blocked  spread       : %d", g_stat_blocked_spread);
   Print("══════════════════════════════════════════════════════════════════");
}
