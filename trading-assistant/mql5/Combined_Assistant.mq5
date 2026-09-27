//+------------------------------------------------------------------+
//|                                       Combined_Assistant.mq5      |
//|  Alert-only trade assistant running Strategy 1, 2, and 3 at the   |
//|  same time. Every alert is tagged with which strategy fired it.   |
//|  This Expert Advisor NEVER calls OrderSend.                        |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Runs Strategy 1, 2, and 3 together and raises a tagged alert for whichever one fires. Does not place trades."

//----- Strategy 1 inputs
input int    InpS1Lookback       = 20;
input double InpS1ToleranceRatio = 0.15;

//----- Strategy 2 inputs
input int    InpS2ConfirmBars    = 2;
input double InpS2FvgBufferRatio = 0.25;
input double InpS2RewardMultiple = 2.0;

//----- Strategy 3 inputs
input int    InpS3Lookback       = 20;
input double InpS3ToleranceRatio = 0.15;
input int    InpS3MaxWaitBars    = 10;

input bool   InpUsePushNotify    = false;

datetime g_lastProcessedBarTime = 0;

// Strategy 1 state
bool     g_s1PendingSweep     = false;
string   g_s1PendingDirection = "";
datetime g_s1PendingSweepTime = 0;

// Strategy 2 state
double   g_s2LastSwingHigh = 0.0;
bool     g_s2HaveSwingHigh = false;
double   g_s2LastSwingLow  = 0.0;
bool     g_s2HaveSwingLow  = false;
bool     g_s2ActiveFvg      = false;
string   g_s2FvgDirection   = "";
double   g_s2FvgTop         = 0.0;
double   g_s2FvgBottom      = 0.0;
double   g_s2ImpulseExtreme = 0.0;

// Strategy 3 state
bool     g_s3PendingCandle     = false;
datetime g_s3PendingCandleTime = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_lastProcessedBarTime = 0;
   g_s1PendingSweep = false;
   g_s2HaveSwingHigh = false;
   g_s2HaveSwingLow  = false;
   g_s2ActiveFvg     = false;
   g_s3PendingCandle = false;
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
}

//+------------------------------------------------------------------+
//| Shared helpers                                                    |
//+------------------------------------------------------------------+
double SwingHigh(const int shift, const int lookback)
{
   int idx = iHighest(_Symbol, _Period, MODE_HIGH, lookback, shift + 1);
   if(idx < 0) return(0.0);
   return(iHigh(_Symbol, _Period, idx));
}

double SwingLow(const int shift, const int lookback)
{
   int idx = iLowest(_Symbol, _Period, MODE_LOW, lookback, shift + 1);
   if(idx < 0) return(0.0);
   return(iLow(_Symbol, _Period, idx));
}

string DetectSweep(const int shift, const double levelHigh, const double levelLow)
{
   double high  = iHigh(_Symbol, _Period, shift);
   double low   = iLow(_Symbol, _Period, shift);
   double close = iClose(_Symbol, _Period, shift);
   if(high > levelHigh && close < levelHigh) return("bearish");
   if(low < levelLow && close > levelLow) return("bullish");
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
   if(range <= 0.0) return(false);
   return(MathAbs(upper - lower) <= toleranceRatio * range);
}

void DrawRing(const string name, const int shift, const color clr)
{
   datetime barTime = iTime(_Symbol, _Period, shift);
   double   high     = iHigh(_Symbol, _Period, shift);
   double   low      = iLow(_Symbol, _Period, shift);
   double   padding  = (high - low) * 0.15;
   int      halfBar  = PeriodSeconds(_Period) / 2;

   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_ELLIPSE, 0,
                   barTime - halfBar, high + padding,
                   barTime + halfBar, low - padding);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, name, OBJPROP_FILL, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }
}

void RaiseAlert(const string message)
{
   Alert(message);
   Print(message);
   if(InpUsePushNotify)
      SendNotification(message);
}

//+------------------------------------------------------------------+
//| Strategy 1: sweep + equal-wick candle                             |
//+------------------------------------------------------------------+
void RunStrategy1(const int shift)
{
   if(g_s1PendingSweep)
   {
      if(IsEqualWick(shift, InpS1ToleranceRatio))
      {
         datetime barTime = iTime(_Symbol, _Period, shift);
         DrawRing("C_S1_" + TimeToString(barTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS), shift,
                  (g_s1PendingDirection == "bullish") ? clrLimeGreen : clrOrangeRed);
         RaiseAlert(StringFormat(
            "[Strategy 1] %s: sweep at %s, equal-wick confirmation at %s on %s %s",
            g_s1PendingDirection,
            TimeToString(g_s1PendingSweepTime, TIME_DATE | TIME_MINUTES),
            TimeToString(barTime, TIME_DATE | TIME_MINUTES),
            _Symbol, EnumToString(_Period)));
      }
      g_s1PendingSweep = false;
      g_s1PendingDirection = "";
      return;
   }

   double levelHigh = SwingHigh(shift, InpS1Lookback);
   double levelLow  = SwingLow(shift, InpS1Lookback);
   string direction = DetectSweep(shift, levelHigh, levelLow);
   if(direction != "")
   {
      g_s1PendingSweep     = true;
      g_s1PendingDirection = direction;
      g_s1PendingSweepTime = iTime(_Symbol, _Period, shift);
   }
}

//+------------------------------------------------------------------+
//| Strategy 2: BOS + FVG retest                                      |
//+------------------------------------------------------------------+
bool S2IsConfirmedSwingHigh(const int shift, const int confirmBars)
{
   double peak = iHigh(_Symbol, _Period, shift);
   for(int k = 1; k <= confirmBars; k++)
   {
      if(iHigh(_Symbol, _Period, shift + k) >= peak) return(false);
      if(iHigh(_Symbol, _Period, shift - k) >= peak) return(false);
   }
   return(true);
}

bool S2IsConfirmedSwingLow(const int shift, const int confirmBars)
{
   double trough = iLow(_Symbol, _Period, shift);
   for(int k = 1; k <= confirmBars; k++)
   {
      if(iLow(_Symbol, _Period, shift + k) <= trough) return(false);
      if(iLow(_Symbol, _Period, shift - k) <= trough) return(false);
   }
   return(true);
}

bool S2FindFvgAt(const int shift, const string direction, double &top, double &bottom)
{
   double aHigh = iHigh(_Symbol, _Period, shift + 2);
   double aLow  = iLow(_Symbol, _Period, shift + 2);
   double cHigh = iHigh(_Symbol, _Period, shift);
   double cLow  = iLow(_Symbol, _Period, shift);
   if(direction == "bullish" && aHigh < cLow) { top = cLow; bottom = aHigh; return(true); }
   if(direction == "bearish" && aLow > cHigh) { top = aLow; bottom = cHigh; return(true); }
   return(false);
}

void S2DrawLevel(const string name, const double price, const color clr)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }
   else
   {
      ObjectSetDouble(0, name, OBJPROP_PRICE, 0, price);
   }
}

void RunStrategy2(const int shift)
{
   int candidateShift = shift + InpS2ConfirmBars;
   if(S2IsConfirmedSwingHigh(candidateShift, InpS2ConfirmBars))
   {
      g_s2LastSwingHigh = iHigh(_Symbol, _Period, candidateShift);
      g_s2HaveSwingHigh = true;
   }
   if(S2IsConfirmedSwingLow(candidateShift, InpS2ConfirmBars))
   {
      g_s2LastSwingLow = iLow(_Symbol, _Period, candidateShift);
      g_s2HaveSwingLow = true;
   }

   double close = iClose(_Symbol, _Period, shift);
   double high  = iHigh(_Symbol, _Period, shift);
   double low   = iLow(_Symbol, _Period, shift);

   if(g_s2ActiveFvg)
   {
      bool touched;
      if(g_s2FvgDirection == "bullish")
      {
         g_s2ImpulseExtreme = MathMax(g_s2ImpulseExtreme, high);
         touched = (low <= g_s2FvgTop && high >= g_s2FvgBottom);
      }
      else
      {
         g_s2ImpulseExtreme = MathMin(g_s2ImpulseExtreme, low);
         touched = (high >= g_s2FvgBottom && low <= g_s2FvgTop);
      }

      if(touched)
      {
         double buffer = (g_s2FvgTop - g_s2FvgBottom) * InpS2FvgBufferRatio;
         double entry, stopLoss, tp1, tp2, rewardLeg;

         if(g_s2FvgDirection == "bullish")
         {
            entry = g_s2FvgTop; stopLoss = g_s2FvgBottom - buffer; tp1 = g_s2ImpulseExtreme;
            rewardLeg = MathAbs(tp1 - entry); tp2 = entry + InpS2RewardMultiple * rewardLeg;
         }
         else
         {
            entry = g_s2FvgBottom; stopLoss = g_s2FvgTop + buffer; tp1 = g_s2ImpulseExtreme;
            rewardLeg = MathAbs(tp1 - entry); tp2 = entry - InpS2RewardMultiple * rewardLeg;
         }

         string tag = TimeToString(iTime(_Symbol, _Period, shift), TIME_DATE | TIME_MINUTES | TIME_SECONDS);
         S2DrawLevel("C_S2_Entry_" + tag, entry, clrDodgerBlue);
         S2DrawLevel("C_S2_SL_"    + tag, stopLoss, clrCrimson);
         S2DrawLevel("C_S2_TP1_"   + tag, tp1, clrLimeGreen);
         S2DrawLevel("C_S2_TP2_"   + tag, tp2, clrLimeGreen);

         RaiseAlert(StringFormat(
            "[Strategy 2] %s retest on %s %s: entry %.5f, SL %.5f, TP1 %.5f, TP2 %.5f",
            g_s2FvgDirection, _Symbol, EnumToString(_Period), entry, stopLoss, tp1, tp2));

         g_s2ActiveFvg = false;
      }
      return;
   }

   if(g_s2HaveSwingHigh && close > g_s2LastSwingHigh)
   {
      double top, bottom;
      if(S2FindFvgAt(shift, "bullish", top, bottom))
      {
         g_s2ActiveFvg = true; g_s2FvgDirection = "bullish";
         g_s2FvgTop = top; g_s2FvgBottom = bottom; g_s2ImpulseExtreme = high;
      }
      g_s2HaveSwingHigh = false;
   }
   else if(g_s2HaveSwingLow && close < g_s2LastSwingLow)
   {
      double top, bottom;
      if(S2FindFvgAt(shift, "bearish", top, bottom))
      {
         g_s2ActiveFvg = true; g_s2FvgDirection = "bearish";
         g_s2FvgTop = top; g_s2FvgBottom = bottom; g_s2ImpulseExtreme = low;
      }
      g_s2HaveSwingLow = false;
   }
}

//+------------------------------------------------------------------+
//| Strategy 3: equal-wick candle confirmed by a sweep afterward       |
//+------------------------------------------------------------------+
void RunStrategy3(const int shift)
{
   if(g_s3PendingCandle)
   {
      int pendingShiftNow = iBarShift(_Symbol, _Period, g_s3PendingCandleTime, true);
      int barsWaited       = pendingShiftNow - 1;
      if(barsWaited > InpS3MaxWaitBars)
         g_s3PendingCandle = false;
   }

   if(g_s3PendingCandle)
   {
      double levelHigh = SwingHigh(shift, InpS3Lookback);
      double levelLow  = SwingLow(shift, InpS3Lookback);
      string direction = DetectSweep(shift, levelHigh, levelLow);

      if(direction != "")
      {
         datetime barTime = iTime(_Symbol, _Period, shift);
         DrawRing("C_S3_" + TimeToString(barTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS), shift,
                  (direction == "bullish") ? clrLimeGreen : clrOrangeRed);
         RaiseAlert(StringFormat(
            "[Strategy 3] %s: candle at %s confirmed by sweep at %s on %s %s",
            direction, TimeToString(g_s3PendingCandleTime, TIME_DATE | TIME_MINUTES),
            TimeToString(barTime, TIME_DATE | TIME_MINUTES), _Symbol, EnumToString(_Period)));
         g_s3PendingCandle = false;
         return;
      }
   }

   if(!g_s3PendingCandle && IsEqualWick(shift, InpS3ToleranceRatio))
   {
      g_s3PendingCandle     = true;
      g_s3PendingCandleTime = iTime(_Symbol, _Period, shift);
   }
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
   int required = MathMax(InpS1Lookback, MathMax(2 * InpS2ConfirmBars + 3, InpS3Lookback)) + shift + 1;
   if(Bars(_Symbol, _Period) < required)
      return;

   RunStrategy1(shift);
   RunStrategy2(shift);
   RunStrategy3(shift);
}
