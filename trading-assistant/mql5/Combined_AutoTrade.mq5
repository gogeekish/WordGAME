//+------------------------------------------------------------------+
//|                                       Combined_AutoTrade.mq5      |
//|  Auto-trade version running Strategy 1, 2, and 3 together. The    |
//|  first one to confirm gets traded; all detection pauses while     |
//|  that position is open, then resumes fresh once flat again (the   |
//|  "reboot"). NOT compiler-verified in this environment - test on   |
//|  a DEMO account first, for a while, before ever going live.       |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Runs Strategy 1, 2, and 3 together and trades whichever one confirms first. Test on a demo account first."

#include <Trade\Trade.mqh>
#include "RiskGate.mqh"

//----- Strategy 1 inputs
input int    InpS1Lookback       = 20;
input double InpS1ToleranceRatio = 0.15;
input double InpS1StopDistance   = 100;    // points

//----- Strategy 2 inputs
input int    InpS2ConfirmBars    = 2;
input double InpS2FvgBufferRatio = 0.25;

//----- Strategy 3 inputs
input int    InpS3Lookback       = 20;
input double InpS3ToleranceRatio = 0.15;
input int    InpS3MaxWaitBars    = 10;
input double InpS3StopDistance   = 100;    // points

//----- Shared inputs
input double InpRewardMultiple = 2.0;      // Used by all three for their TP distance
input double InpVolume         = 0.01;     // Lots per trade
input ulong  InpMagicNumber    = 20260199;
input bool   InpUsePushNotify  = false;
input int    InpCooldownBars         = 5;  // Bars to wait after a LOSS before trading again (shared across all 3)
input int    InpMaxConsecutiveLosses = 3;  // Halt entirely after this many losses in a row (needs a manual restart)

CTrade   g_trade;
CRiskGate g_riskGate;
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
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_riskGate.Init(InpCooldownBars, InpMaxConsecutiveLosses);
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

bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      return(true);
   }
   return(false);
}

void PlaceTrade(const string strategyTag, const string direction, const double stopLoss, const double takeProfit)
{
   double price;
   bool   sent;

   if(direction == "bullish")
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sent  = g_trade.Buy(InpVolume, _Symbol, price, stopLoss, takeProfit, strategyTag + " auto (combined)");
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sent  = g_trade.Sell(InpVolume, _Symbol, price, stopLoss, takeProfit, strategyTag + " auto (combined)");
   }

   if(!sent)
   {
      Print(strategyTag, " auto (combined): order failed, retcode=", g_trade.ResultRetcode(),
            " ", g_trade.ResultRetcodeDescription());
      return;
   }

   string message = StringFormat(
      "%s auto (combined) (%s): entered at %.5f, SL %.5f, TP %.5f on %s %s",
      strategyTag, direction, price, stopLoss, takeProfit, _Symbol, EnumToString(_Period));
   Print(message);
   if(InpUsePushNotify)
      SendNotification(message);
}

//+------------------------------------------------------------------+
//| Strategy 1: sweep + equal-wick candle. Returns true if it traded. |
//+------------------------------------------------------------------+
bool RunStrategy1(const int shift)
{
   if(g_s1PendingSweep)
   {
      bool traded = false;
      if(IsEqualWick(shift, InpS1ToleranceRatio))
      {
         double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
         double stopDistance = InpS1StopDistance * point;
         double price = (g_s1PendingDirection == "bullish")
                         ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double sl = (g_s1PendingDirection == "bullish") ? price - stopDistance : price + stopDistance;
         double tp = (g_s1PendingDirection == "bullish")
                     ? price + stopDistance * InpRewardMultiple
                     : price - stopDistance * InpRewardMultiple;
         PlaceTrade("Strategy 1", g_s1PendingDirection, sl, tp);
         traded = true;
      }
      g_s1PendingSweep = false;
      g_s1PendingDirection = "";
      return(traded);
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
   return(false);
}

//+------------------------------------------------------------------+
//| Strategy 2: BOS + FVG retest. Returns true if it traded.           |
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

bool RunStrategy2(const int shift)
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
            rewardLeg = MathAbs(tp1 - entry); tp2 = entry + InpRewardMultiple * rewardLeg;
         }
         else
         {
            entry = g_s2FvgBottom; stopLoss = g_s2FvgTop + buffer; tp1 = g_s2ImpulseExtreme;
            rewardLeg = MathAbs(tp1 - entry); tp2 = entry - InpRewardMultiple * rewardLeg;
         }

         PlaceTrade("Strategy 2", g_s2FvgDirection, stopLoss, tp2);
         g_s2ActiveFvg = false;
         return(true);
      }
      return(false);
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
   return(false);
}

//+------------------------------------------------------------------+
//| Strategy 3: equal-wick candle confirmed by a sweep afterward.     |
//| Returns true if it traded.                                        |
//+------------------------------------------------------------------+
bool RunStrategy3(const int shift)
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
         double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
         double stopDistance = InpS3StopDistance * point;
         double price = (direction == "bullish")
                         ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double sl = (direction == "bullish") ? price - stopDistance : price + stopDistance;
         double tp = (direction == "bullish")
                     ? price + stopDistance * InpRewardMultiple
                     : price - stopDistance * InpRewardMultiple;
         PlaceTrade("Strategy 3", direction, sl, tp);
         g_s3PendingCandle = false;
         return(true);
      }
   }

   if(!g_s3PendingCandle && IsEqualWick(shift, InpS3ToleranceRatio))
   {
      g_s3PendingCandle     = true;
      g_s3PendingCandleTime = iTime(_Symbol, _Period, shift);
   }
   return(false);
}

//+------------------------------------------------------------------+
//| Runs once per closed bar. While a position from this EA is open,  |
//| detection for all three strategies is paused entirely - it        |
//| resumes fresh once flat again. Whichever strategy confirms first  |
//| on a given bar gets the trade; the arbitrary tie-break order when |
//| more than one confirms on the very same bar is Strategy 1, then   |
//| Strategy 2, then Strategy 3. One shared CRiskGate (RiskGate.mqh)  |
//| covers all three: a cooldown after any loss, and a hard stop      |
//| after too many losses in a row from any of them combined.         |
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
      string haltMsg = StringFormat("Combined auto: HALTED - %s. Call g_riskGate.Reset() (or restart the EA) to resume.",
                                     g_riskGate.HaltedReason());
      Alert(haltMsg);
      Print(haltMsg);
   }

   if(HasOpenPosition())
      return; // already in a trade from one of the three - wait for it to close (the reboot)
   if(!g_riskGate.CanTrade())
      return; // cooling down after a loss, or halted - see RiskGate.mqh

   int shift = 1; // the bar that just closed
   int required = MathMax(InpS1Lookback, MathMax(2 * InpS2ConfirmBars + 3, InpS3Lookback)) + shift + 1;
   if(Bars(_Symbol, _Period) < required)
      return;

   if(RunStrategy1(shift))
      return;
   if(RunStrategy2(shift))
      return;
   RunStrategy3(shift);
}
