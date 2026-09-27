//+------------------------------------------------------------------+
//|                                  Strategy2_BOS_FVG_Assistant.mq5  |
//|  Alert-only trade assistant: Break of Structure + Fair Value Gap  |
//|  retest. This Expert Advisor NEVER calls OrderSend - it only      |
//|  marks the chart and raises an alert so you can decide yourself.  |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Watches for a BOS, finds the FVG it left behind, and alerts when price retests it. Does not place trades."

input int    InpConfirmBars    = 2;     // Bars each side needed to confirm a swing high/low
input double InpFvgBufferRatio = 0.25;  // Stop-loss buffer beyond the FVG, as a fraction of its height
input double InpRewardMultiple = 2.0;   // TP2 distance as a multiple of the entry-to-TP1 distance
input bool   InpUsePushNotify  = false; // Also send a push notification (requires MetaTrader setup)

datetime g_lastProcessedBarTime = 0;

double   g_lastSwingHigh = 0.0;
bool     g_haveSwingHigh = false;
double   g_lastSwingLow  = 0.0;
bool     g_haveSwingLow  = false;

bool     g_activeFvg      = false;
string   g_fvgDirection   = "";
double   g_fvgTop         = 0.0;
double   g_fvgBottom      = 0.0;
double   g_impulseExtreme = 0.0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_lastProcessedBarTime = 0;
   g_haveSwingHigh = false;
   g_haveSwingLow  = false;
   g_activeFvg     = false;
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
}

//+------------------------------------------------------------------+
//| True if the bar at `shift` is a confirmed swing high: every bar   |
//| within `confirmBars` on both sides has a lower high.              |
//+------------------------------------------------------------------+
bool IsConfirmedSwingHigh(const int shift, const int confirmBars)
{
   double peak = iHigh(_Symbol, _Period, shift);
   for(int k = 1; k <= confirmBars; k++)
   {
      if(iHigh(_Symbol, _Period, shift + k) >= peak) return(false); // older bar
      if(iHigh(_Symbol, _Period, shift - k) >= peak) return(false); // newer bar
   }
   return(true);
}

//+------------------------------------------------------------------+
//| True if the bar at `shift` is a confirmed swing low: every bar    |
//| within `confirmBars` on both sides has a higher low.              |
//+------------------------------------------------------------------+
bool IsConfirmedSwingLow(const int shift, const int confirmBars)
{
   double trough = iLow(_Symbol, _Period, shift);
   for(int k = 1; k <= confirmBars; k++)
   {
      if(iLow(_Symbol, _Period, shift + k) <= trough) return(false);
      if(iLow(_Symbol, _Period, shift - k) <= trough) return(false);
   }
   return(true);
}

//+------------------------------------------------------------------+
//| Classic 3-candle Fair Value Gap ending exactly on `shift`.        |
//+------------------------------------------------------------------+
bool FindFvgAt(const int shift, const string direction, double &top, double &bottom)
{
   double aHigh = iHigh(_Symbol, _Period, shift + 2);
   double aLow  = iLow(_Symbol, _Period, shift + 2);
   double cHigh = iHigh(_Symbol, _Period, shift);
   double cLow  = iLow(_Symbol, _Period, shift);

   if(direction == "bullish" && aHigh < cLow)
   {
      top    = cLow;
      bottom = aHigh;
      return(true);
   }
   if(direction == "bearish" && aLow > cHigh)
   {
      top    = aLow;
      bottom = cHigh;
      return(true);
   }
   return(false);
}

//+------------------------------------------------------------------+
void DrawLevel(const string name, const double price, const color clr, const string label)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, name, OBJPROP_TEXT, label);
   }
   else
   {
      ObjectSetDouble(0, name, OBJPROP_PRICE, 0, price);
   }
}

//+------------------------------------------------------------------+
void RaiseRetestSignal(const datetime barTime, const string direction,
                        const double entry, const double stopLoss,
                        const double tp1, const double tp2)
{
   string tag = TimeToString(barTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS);

   DrawLevel("S2_Entry_" + tag, entry,    clrDodgerBlue, "S2 ENTRY");
   DrawLevel("S2_SL_"    + tag, stopLoss, clrCrimson,    "S2 SL");
   DrawLevel("S2_TP1_"   + tag, tp1,      clrLimeGreen,  "S2 TP1");
   DrawLevel("S2_TP2_"   + tag, tp2,      clrLimeGreen,  "S2 TP2");

   string message = StringFormat(
      "Strategy 2 (%s) retest on %s %s: entry %.5f, SL %.5f, TP1 %.5f, TP2 %.5f",
      direction, _Symbol, EnumToString(_Period), entry, stopLoss, tp1, tp2);

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
   if(Bars(_Symbol, _Period) < 2 * InpConfirmBars + shift + 3)
      return; // not enough history yet

   int candidateShift = shift + InpConfirmBars;
   if(IsConfirmedSwingHigh(candidateShift, InpConfirmBars))
   {
      g_lastSwingHigh = iHigh(_Symbol, _Period, candidateShift);
      g_haveSwingHigh = true;
   }
   if(IsConfirmedSwingLow(candidateShift, InpConfirmBars))
   {
      g_lastSwingLow = iLow(_Symbol, _Period, candidateShift);
      g_haveSwingLow = true;
   }

   double close = iClose(_Symbol, _Period, shift);
   double high  = iHigh(_Symbol, _Period, shift);
   double low   = iLow(_Symbol, _Period, shift);

   if(g_activeFvg)
   {
      bool touched;
      if(g_fvgDirection == "bullish")
      {
         g_impulseExtreme = MathMax(g_impulseExtreme, high);
         touched = (low <= g_fvgTop && high >= g_fvgBottom);
      }
      else
      {
         g_impulseExtreme = MathMin(g_impulseExtreme, low);
         touched = (high >= g_fvgBottom && low <= g_fvgTop);
      }

      if(touched)
      {
         double buffer = (g_fvgTop - g_fvgBottom) * InpFvgBufferRatio;
         double entry, stopLoss, tp1, tp2, rewardLeg;

         if(g_fvgDirection == "bullish")
         {
            entry     = g_fvgTop;
            stopLoss  = g_fvgBottom - buffer;
            tp1       = g_impulseExtreme;
            rewardLeg = MathAbs(tp1 - entry);
            tp2       = entry + InpRewardMultiple * rewardLeg;
         }
         else
         {
            entry     = g_fvgBottom;
            stopLoss  = g_fvgTop + buffer;
            tp1       = g_impulseExtreme;
            rewardLeg = MathAbs(tp1 - entry);
            tp2       = entry - InpRewardMultiple * rewardLeg;
         }

         RaiseRetestSignal(iTime(_Symbol, _Period, shift), g_fvgDirection, entry, stopLoss, tp1, tp2);
         g_activeFvg = false;
      }
      return;
   }

   if(g_haveSwingHigh && close > g_lastSwingHigh)
   {
      double top, bottom;
      if(FindFvgAt(shift, "bullish", top, bottom))
      {
         g_activeFvg      = true;
         g_fvgDirection   = "bullish";
         g_fvgTop         = top;
         g_fvgBottom      = bottom;
         g_impulseExtreme = high;
      }
      g_haveSwingHigh = false;
   }
   else if(g_haveSwingLow && close < g_lastSwingLow)
   {
      double top, bottom;
      if(FindFvgAt(shift, "bearish", top, bottom))
      {
         g_activeFvg      = true;
         g_fvgDirection   = "bearish";
         g_fvgTop         = top;
         g_fvgBottom      = bottom;
         g_impulseExtreme = low;
      }
      g_haveSwingLow = false;
   }
}
