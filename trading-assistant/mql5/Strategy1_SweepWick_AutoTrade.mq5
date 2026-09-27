//+------------------------------------------------------------------+
//|                            Strategy1_SweepWick_AutoTrade.mq5      |
//|  Auto-trade version: liquidity sweep + equal-wick candle. Places  |
//|  a real market order with a stop loss and take profit, then       |
//|  waits for that position to close before watching again (the      |
//|  "reboot"). NOT compiler-verified in this environment - test on   |
//|  a DEMO account first, for a while, before ever going live.       |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Places a trade automatically when a liquidity sweep is followed by an equal-wick candle. Test on a demo account first."

#include <Trade\Trade.mqh>
#include "RiskGate.mqh"

input int    InpLookback       = 20;      // Bars used to find the recent swing high/low
input double InpToleranceRatio = 0.15;    // Max allowed wick difference, as a fraction of candle range
input double InpVolume         = 0.01;    // Lots per trade
input double InpStopDistance   = 100;     // Stop-loss distance, in points - tune per symbol
input double InpRewardMultiple = 2.0;     // Take-profit distance = stop distance x this
input ulong  InpMagicNumber    = 20260101;
input bool   InpUsePushNotify  = false;   // Also send a push notification (requires MetaTrader setup)
input int    InpCooldownBars         = 5; // Bars to wait after a LOSS before trading again
input int    InpMaxConsecutiveLosses = 3; // Halt entirely after this many losses in a row (needs a manual restart)

CTrade   g_trade;
CRiskGate g_riskGate;
datetime g_lastProcessedBarTime = 0;
bool     g_pendingSweep         = false;
string   g_pendingDirection     = "";
datetime g_pendingSweepTime     = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_riskGate.Init(InpCooldownBars, InpMaxConsecutiveLosses);
   g_lastProcessedBarTime = 0;
   g_pendingSweep = false;
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
}

//+------------------------------------------------------------------+
double SwingHigh(const int shift, const int lookback)
{
   int idx = iHighest(_Symbol, _Period, MODE_HIGH, lookback, shift + 1);
   if(idx < 0)
      return(0.0);
   return(iHigh(_Symbol, _Period, idx));
}

double SwingLow(const int shift, const int lookback)
{
   int idx = iLowest(_Symbol, _Period, MODE_LOW, lookback, shift + 1);
   if(idx < 0)
      return(0.0);
   return(iLow(_Symbol, _Period, idx));
}

string DetectSweep(const int shift, const double levelHigh, const double levelLow)
{
   double high  = iHigh(_Symbol, _Period, shift);
   double low   = iLow(_Symbol, _Period, shift);
   double close = iClose(_Symbol, _Period, shift);

   if(high > levelHigh && close < levelHigh)
      return("bearish");
   if(low < levelLow && close > levelLow)
      return("bullish");
   return("");
}

void CandleWicks(const int shift, double &upper, double &lower)
{
   double open  = iOpen(_Symbol, _Period, shift);
   double close = iClose(_Symbol, _Period, shift);
   double high  = iHigh(_Symbol, _Period, shift);
   double low   = iLow(_Symbol, _Period, shift);

   double bodyTop    = MathMax(open, close);
   double bodyBottom = MathMin(open, close);
   upper = high - bodyTop;
   lower = bodyBottom - low;
}

bool IsEqualWick(const int shift, const double toleranceRatio)
{
   double upper, lower;
   CandleWicks(shift, upper, lower);

   double range = iHigh(_Symbol, _Period, shift) - iLow(_Symbol, _Period, shift);
   if(range <= 0.0)
      return(false);

   return(MathAbs(upper - lower) <= toleranceRatio * range);
}

//+------------------------------------------------------------------+
//| True if this EA already has an open position on this symbol.     |
//+------------------------------------------------------------------+
bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      return(true);
   }
   return(false);
}

//+------------------------------------------------------------------+
//| Places a market order in `direction` with SL/TP built from        |
//| InpStopDistance/InpRewardMultiple. Never called while a position  |
//| from this EA is already open.                                     |
//+------------------------------------------------------------------+
void PlaceTrade(const string direction, const datetime sweepTime)
{
   double point        = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double stopDistance  = InpStopDistance * point;
   double price, sl, tp;
   bool   sent;

   if(direction == "bullish")
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl    = price - stopDistance;
      tp    = price + stopDistance * InpRewardMultiple;
      sent  = g_trade.Buy(InpVolume, _Symbol, price, sl, tp, "Strategy1 auto");
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = price + stopDistance;
      tp    = price - stopDistance * InpRewardMultiple;
      sent  = g_trade.Sell(InpVolume, _Symbol, price, sl, tp, "Strategy1 auto");
   }

   if(!sent)
   {
      Print("Strategy 1 auto: order failed, retcode=", g_trade.ResultRetcode(),
            " ", g_trade.ResultRetcodeDescription());
      return;
   }

   string message = StringFormat(
      "Strategy 1 auto (%s): entered at %.5f, SL %.5f, TP %.5f on %s %s (sweep at %s)",
      direction, price, sl, tp, _Symbol, EnumToString(_Period),
      TimeToString(sweepTime, TIME_DATE | TIME_MINUTES));

   Print(message);
   if(InpUsePushNotify)
      SendNotification(message);
}

//+------------------------------------------------------------------+
//| Runs once per closed bar. While a position from this EA is open,  |
//| detection is paused entirely - it resumes fresh once flat again.  |
//| A cooldown after a loss, and a hard stop after too many losses in |
//| a row, both come from CRiskGate (RiskGate.mqh) - see that file    |
//| for the rules, which match risk_gate.py's Python version.         |
//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_lastProcessedBarTime)
      return;
   g_lastProcessedBarTime = currentBarTime;

   g_riskGate.AdvanceBar();
   g_riskGate.CheckClosedTrades(_Symbol, InpMagicNumber);
   if(g_riskGate.ConsumeJustHalted())
   {
      string haltMsg = StringFormat("Strategy 1 auto: HALTED - %s. Call g_riskGate.Reset() (or restart the EA) to resume.",
                                     g_riskGate.HaltedReason());
      Alert(haltMsg);
      Print(haltMsg);
   }

   if(HasOpenPosition())
      return; // already in a trade - wait for it to close (the reboot)
   if(!g_riskGate.CanTrade())
      return; // cooling down after a loss, or halted - see RiskGate.mqh

   int shift = 1; // the bar that just closed
   if(Bars(_Symbol, _Period) < InpLookback + shift + 1)
      return;

   if(g_pendingSweep)
   {
      if(IsEqualWick(shift, InpToleranceRatio))
         PlaceTrade(g_pendingDirection, g_pendingSweepTime);

      g_pendingSweep     = false;
      g_pendingDirection = "";
      return;
   }

   double levelHigh = SwingHigh(shift, InpLookback);
   double levelLow  = SwingLow(shift, InpLookback);
   string direction = DetectSweep(shift, levelHigh, levelLow);

   if(direction != "")
   {
      g_pendingSweep     = true;
      g_pendingDirection = direction;
      g_pendingSweepTime = iTime(_Symbol, _Period, shift);
   }
}
