//+------------------------------------------------------------------+
//|                                Strategy1_SweepWick_Assistant.mq5  |
//|  Alert-only trade assistant: liquidity sweep + equal-wick candle. |
//|  This Expert Advisor NEVER calls OrderSend - it only marks the    |
//|  chart and raises an alert so you can decide whether to trade.    |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Watches for a liquidity sweep followed by an equal-wick candle and raises an alert. Does not place trades."

input int    InpLookback       = 20;    // Bars used to find the recent swing high/low
input double InpToleranceRatio = 0.15;  // Max allowed wick difference, as a fraction of candle range
input bool   InpUsePushNotify  = false; // Also send a push notification (requires MetaTrader setup)

datetime g_lastProcessedBarTime = 0;
bool     g_pendingSweep         = false;
string   g_pendingDirection     = "";
datetime g_pendingSweepTime     = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_lastProcessedBarTime = 0;
   g_pendingSweep = false;
   g_pendingDirection = "";
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
}

//+------------------------------------------------------------------+
//| Highest high over InpLookback bars strictly before `shift`.       |
//+------------------------------------------------------------------+
double SwingHigh(const int shift, const int lookback)
{
   int idx = iHighest(_Symbol, _Period, MODE_HIGH, lookback, shift + 1);
   if(idx < 0)
      return(0.0);
   return(iHigh(_Symbol, _Period, idx));
}

//+------------------------------------------------------------------+
//| Lowest low over InpLookback bars strictly before `shift`.         |
//+------------------------------------------------------------------+
double SwingLow(const int shift, const int lookback)
{
   int idx = iLowest(_Symbol, _Period, MODE_LOW, lookback, shift + 1);
   if(idx < 0)
      return(0.0);
   return(iLow(_Symbol, _Period, idx));
}

//+------------------------------------------------------------------+
//| "bearish" if the candle swept the high and closed back below it,  |
//| "bullish" if it swept the low and closed back above it, else "".  |
//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
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
//| Draws a ring around the signal candle and raises the alert.       |
//+------------------------------------------------------------------+
void MarkSignal(const int shift, const string direction, const datetime sweepTime)
{
   datetime barTime = iTime(_Symbol, _Period, shift);
   double   high     = iHigh(_Symbol, _Period, shift);
   double   low      = iLow(_Symbol, _Period, shift);
   double   padding  = (high - low) * 0.15;
   int      halfBar  = PeriodSeconds(_Period) / 2;

   string name = "S1_Signal_" + TimeToString(barTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS);
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_ELLIPSE, 0,
                   barTime - halfBar, high + padding,
                   barTime + halfBar, low - padding);
      color clr = (direction == "bullish") ? clrLimeGreen : clrOrangeRed;
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, name, OBJPROP_FILL, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }

   string message = StringFormat(
      "Strategy 1 (%s): sweep at %s, equal-wick confirmation at %s on %s %s",
      direction,
      TimeToString(sweepTime, TIME_DATE | TIME_MINUTES),
      TimeToString(barTime, TIME_DATE | TIME_MINUTES),
      _Symbol, EnumToString(_Period));

   Alert(message);
   Print(message);
   if(InpUsePushNotify)
      SendNotification(message);
}

//+------------------------------------------------------------------+
//| Runs once per closed bar. Never places a trade.                   |
//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_lastProcessedBarTime)
      return; // still the same forming bar, wait for it to close
   g_lastProcessedBarTime = currentBarTime;

   int shift = 1; // the bar that just closed
   if(Bars(_Symbol, _Period) < InpLookback + shift + 1)
      return; // not enough history yet

   if(g_pendingSweep)
   {
      if(IsEqualWick(shift, InpToleranceRatio))
         MarkSignal(shift, g_pendingDirection, g_pendingSweepTime);

      g_pendingSweep = false;
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
