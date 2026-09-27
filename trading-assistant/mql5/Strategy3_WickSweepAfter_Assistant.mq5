//+------------------------------------------------------------------+
//|                       Strategy3_WickSweepAfter_Assistant.mq5      |
//|  Alert-only trade assistant: equal-wick candle confirmed by a     |
//|  liquidity sweep afterward. This Expert Advisor NEVER calls       |
//|  OrderSend - it only marks the chart and raises an alert.         |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Watches for an equal-wick candle, then confirms it with a liquidity sweep afterward, and raises an alert. Does not place trades."

input int    InpLookback        = 20;    // Bars used to find the recent swing high/low
input double InpToleranceRatio  = 0.15;  // Max allowed wick difference, as a fraction of candle range
input int    InpMaxWaitBars     = 10;    // Give up waiting for the confirming sweep after this many bars
input bool   InpUsePushNotify   = false; // Also send a push notification (requires MetaTrader setup)

datetime g_lastProcessedBarTime = 0;
bool     g_pendingCandle        = false;
datetime g_pendingCandleTime    = 0;

//+------------------------------------------------------------------+
int OnInit()
{
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
void MarkSignal(const int shift, const string direction, const datetime candleTime)
{
   datetime barTime = iTime(_Symbol, _Period, shift);
   double   high     = iHigh(_Symbol, _Period, shift);
   double   low      = iLow(_Symbol, _Period, shift);
   double   padding  = (high - low) * 0.15;
   int      halfBar  = PeriodSeconds(_Period) / 2;

   string name = "S3_Signal_" + TimeToString(barTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS);
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_ELLIPSE, 0,
                   barTime - halfBar, high + padding,
                   barTime + halfBar, low - padding);
      color clr = (direction == "bullish") ? clrLimeGreen : clrOrangeRed;
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASHDOT);
      ObjectSetInteger(0, name, OBJPROP_FILL, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }

   string message = StringFormat(
      "Strategy 3 (%s): candle at %s confirmed by sweep at %s on %s %s",
      direction,
      TimeToString(candleTime, TIME_DATE | TIME_MINUTES),
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
      return;
   g_lastProcessedBarTime = currentBarTime;

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
         MarkSignal(shift, direction, g_pendingCandleTime);
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
