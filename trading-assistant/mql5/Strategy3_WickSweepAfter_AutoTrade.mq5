//+------------------------------------------------------------------+
//|                        Strategy3_WickSweepAfter_AutoTrade.mq5     |
//|  Auto-trade version: equal-wick candle confirmed by a liquidity   |
//|  sweep afterward. Places a real market order with SL/TP once      |
//|  confirmed, then waits for that position to close before          |
//|  watching again (the "reboot"). NOT compiler-verified in this     |
//|  environment - test on a DEMO account first.                      |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Places a trade automatically when an equal-wick candle is confirmed by a sweep afterward. Test on a demo account first."

#include <Trade\Trade.mqh>

input int    InpLookback       = 20;      // Bars used to find the recent swing high/low
input double InpToleranceRatio = 0.15;    // Max allowed wick difference, as a fraction of candle range
input int    InpMaxWaitBars    = 10;      // Give up waiting for the confirming sweep after this many bars
input double InpVolume         = 0.01;    // Lots per trade
input double InpStopDistance   = 100;     // Stop-loss distance, in points - tune per symbol
input double InpRewardMultiple = 2.0;     // Take-profit distance = stop distance x this
input ulong  InpMagicNumber    = 20260103;
input bool   InpUsePushNotify  = false;   // Also send a push notification (requires MetaTrader setup)

CTrade   g_trade;
datetime g_lastProcessedBarTime = 0;
bool     g_pendingCandle        = false;
datetime g_pendingCandleTime    = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_lastProcessedBarTime = 0;
   g_pendingCandle = false;
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
void PlaceTrade(const string direction, const datetime candleTime)
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
      sent  = g_trade.Buy(InpVolume, _Symbol, price, sl, tp, "Strategy3 auto");
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = price + stopDistance;
      tp    = price - stopDistance * InpRewardMultiple;
      sent  = g_trade.Sell(InpVolume, _Symbol, price, sl, tp, "Strategy3 auto");
   }

   if(!sent)
   {
      Print("Strategy 3 auto: order failed, retcode=", g_trade.ResultRetcode(),
            " ", g_trade.ResultRetcodeDescription());
      return;
   }

   string message = StringFormat(
      "Strategy 3 auto (%s): entered at %.5f, SL %.5f, TP %.5f on %s %s (candle at %s)",
      direction, price, sl, tp, _Symbol, EnumToString(_Period),
      TimeToString(candleTime, TIME_DATE | TIME_MINUTES));

   Print(message);
   if(InpUsePushNotify)
      SendNotification(message);
}

//+------------------------------------------------------------------+
//| Runs once per closed bar. While a position from this EA is open,  |
//| detection is paused entirely - it resumes fresh once flat again.  |
//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_lastProcessedBarTime)
      return;
   g_lastProcessedBarTime = currentBarTime;

   if(HasOpenPosition())
      return; // already in a trade - wait for it to close (the reboot)

   int shift = 1; // the bar that just closed
   if(Bars(_Symbol, _Period) < InpLookback + shift + 1)
      return;

   if(g_pendingCandle)
   {
      int pendingShiftNow = iBarShift(_Symbol, _Period, g_pendingCandleTime, true);
      int barsWaited       = pendingShiftNow - 1;
      if(barsWaited > InpMaxWaitBars)
         g_pendingCandle = false; // gave up waiting for a confirming sweep
   }

   if(g_pendingCandle)
   {
      double levelHigh = SwingHigh(shift, InpLookback);
      double levelLow  = SwingLow(shift, InpLookback);
      string direction = DetectSweep(shift, levelHigh, levelLow);

      if(direction != "")
      {
         PlaceTrade(direction, g_pendingCandleTime);
         g_pendingCandle = false;
         return;
      }
   }

   if(!g_pendingCandle && IsEqualWick(shift, InpToleranceRatio))
   {
      g_pendingCandle     = true;
      g_pendingCandleTime = iTime(_Symbol, _Period, shift);
   }
}
