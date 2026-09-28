//+------------------------------------------------------------------+
//|                              Strategy2_BOS_FVG_AutoTrade.mq5      |
//|  Auto-trade version: Break of Structure + Fair Value Gap retest.  |
//|  Places a real market order with SL/TP2 once a retest is          |
//|  confirmed, then waits for that position to close before          |
//|  watching again (the "reboot"). NOT compiler-verified in this     |
//|  environment - test on a DEMO account first.                      |
//+------------------------------------------------------------------+
#property copyright "Trade Assistant"
#property version   "1.00"
#property description "Places a trade automatically when price retests the FVG left behind by a BOS. Test on a demo account first."

#include <Trade\Trade.mqh>
#include "RiskGate.mqh"

input int    InpConfirmBars    = 2;       // Bars each side needed to confirm a swing high/low
input double InpFvgBufferRatio = 0.25;    // Stop-loss buffer beyond the FVG, as a fraction of its height
input double InpRewardMultiple = 2.0;     // TP2 distance as a multiple of the entry-to-TP1 distance
input double InpVolume         = 0.01;    // Lots per trade
input ulong  InpMagicNumber    = 20260102;
input bool   InpUsePushNotify  = false;   // Also send a push notification (requires MetaTrader setup)
input int    InpCooldownBars         = 5; // Bars to wait after a LOSS before trading again
input int    InpMaxConsecutiveLosses = 5; // Halt entirely after this many losses in a row (needs a manual restart)

#define RESET_BUTTON_NAME "S2_RiskGateResetBtn"

CTrade   g_trade;
CRiskGate g_riskGate;
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
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_riskGate.Init(InpCooldownBars, InpMaxConsecutiveLosses);
   g_riskGate.CreateResetButton(RESET_BUTTON_NAME);
   g_lastProcessedBarTime = 0;
   g_haveSwingHigh = false;
   g_haveSwingLow  = false;
   g_activeFvg     = false;
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   g_riskGate.DeleteResetButton(RESET_BUTTON_NAME);
}

//+------------------------------------------------------------------+
//| Handles clicks on the "Reset Risk Gate" chart button.             |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK && g_riskGate.HandleButtonClick(sparam, RESET_BUTTON_NAME))
   {
      Print("Strategy 2 auto: risk gate manually reset via chart button.");
      ChartRedraw(0);
   }
}

//+------------------------------------------------------------------+
bool IsConfirmedSwingHigh(const int shift, const int confirmBars)
{
   double peak = iHigh(_Symbol, _Period, shift);
   for(int k = 1; k <= confirmBars; k++)
   {
      if(iHigh(_Symbol, _Period, shift + k) >= peak) return(false);
      if(iHigh(_Symbol, _Period, shift - k) >= peak) return(false);
   }
   return(true);
}

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
//| Places a market order in `direction` using the computed SL/TP2.   |
//| The fill price is the current market price, not the exact FVG     |
//| edge - a simplification worth knowing about.                      |
//+------------------------------------------------------------------+
void PlaceTrade(const string direction, const double stopLoss, const double takeProfit)
{
   double price;
   bool   sent;

   if(direction == "bullish")
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sent  = g_trade.Buy(InpVolume, _Symbol, price, stopLoss, takeProfit, "Strategy2 auto");
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sent  = g_trade.Sell(InpVolume, _Symbol, price, stopLoss, takeProfit, "Strategy2 auto");
   }

   if(!sent)
   {
      Print("Strategy 2 auto: order failed, retcode=", g_trade.ResultRetcode(),
            " ", g_trade.ResultRetcodeDescription());
      return;
   }

   string message = StringFormat(
      "Strategy 2 auto (%s): entered at %.5f, SL %.5f, TP %.5f on %s %s",
      direction, price, stopLoss, takeProfit, _Symbol, EnumToString(_Period));

   Print(message);
   if(InpUsePushNotify)
      SendNotification(message);
}

//+------------------------------------------------------------------+
//| Runs once per closed bar. While a position from this EA is open,  |
//| detection is paused entirely - it resumes fresh once flat again.  |
//| A cooldown after a loss, and a hard stop after too many losses in |
//| a row, both come from CRiskGate (RiskGate.mqh).                   |
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
      string haltMsg = StringFormat("Strategy 2 auto: HALTED - %s. Call g_riskGate.Reset() (or restart the EA) to resume.",
                                     g_riskGate.HaltedReason());
      Alert(haltMsg);
      Print(haltMsg);
   }

   if(HasOpenPosition())
      return; // already in a trade - wait for it to close (the reboot)
   if(!g_riskGate.CanTrade())
      return; // cooling down after a loss, or halted - see RiskGate.mqh

   int shift = 1; // the bar that just closed
   if(Bars(_Symbol, _Period) < 2 * InpConfirmBars + shift + 3)
      return;

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

         PlaceTrade(g_fvgDirection, stopLoss, tp2);
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
