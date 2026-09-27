//+------------------------------------------------------------------+
//|                                                   RiskGate.mqh    |
//|  Shared reboot rules for the Auto Trade EAs: a cooldown after a   |
//|  loss, and a hard stop after too many losses in a row. Include    |
//|  this from an EA (it must sit in the same folder as the .mq5      |
//|  file) and:                                                       |
//|    - call AdvanceBar() once per closed bar                        |
//|    - call CheckClosedTrades(symbol, magic) once per closed bar,   |
//|      before checking CanTrade()                                   |
//|    - call CanTrade() before placing an order                      |
//|    - call Reset() to manually clear a halt                        |
//|  This mirrors risk_gate.py's RiskGate class rule for rule, so the |
//|  Python and MQL5 versions behave the same way.                    |
//+------------------------------------------------------------------+
#ifndef RISK_GATE_MQH
#define RISK_GATE_MQH

class CRiskGate
{
private:
   int      m_cooldownBars;
   int      m_maxConsecutiveLosses;
   int      m_consecutiveLosses;
   int      m_barsSinceLoss;   // -1 = no cooldown in progress
   bool     m_halted;
   string   m_haltedReason;
   bool     m_justHalted;
   ulong    m_seenTickets[];

   bool AlreadySeen(const ulong ticket)
   {
      for(int i = 0; i < ArraySize(m_seenTickets); i++)
         if(m_seenTickets[i] == ticket)
            return(true);
      return(false);
   }

   void MarkSeen(const ulong ticket)
   {
      int n = ArraySize(m_seenTickets);
      ArrayResize(m_seenTickets, n + 1);
      m_seenTickets[n] = ticket;
   }

public:
   void Init(const int cooldownBars, const int maxConsecutiveLosses)
   {
      m_cooldownBars         = MathMax(0, cooldownBars);
      m_maxConsecutiveLosses = MathMax(1, maxConsecutiveLosses);
      m_consecutiveLosses    = 0;
      m_barsSinceLoss        = -1;
      m_halted               = false;
      m_haltedReason         = "";
      m_justHalted           = false;
      ArrayResize(m_seenTickets, 0);
   }

   bool   IsHalted() const        { return(m_halted); }
   string HaltedReason() const    { return(m_haltedReason); }
   int    ConsecutiveLosses() const { return(m_consecutiveLosses); }

   bool CanTrade() const
   {
      if(m_halted)
         return(false);
      if(m_barsSinceLoss >= 0 && m_barsSinceLoss < m_cooldownBars)
         return(false);
      return(true);
   }

   void AdvanceBar()
   {
      if(m_barsSinceLoss >= 0)
         m_barsSinceLoss++;
   }

   void RecordOutcome(const bool isLoss)
   {
      if(isLoss)
      {
         m_consecutiveLosses++;
         m_barsSinceLoss = 0;
         if(m_consecutiveLosses >= m_maxConsecutiveLosses && !m_halted)
         {
            m_halted       = true;
            m_justHalted   = true;
            m_haltedReason = StringFormat("%d losses in a row (limit %d)",
                                           m_consecutiveLosses, m_maxConsecutiveLosses);
         }
      }
      else
      {
         m_consecutiveLosses = 0;
         m_barsSinceLoss     = -1;
      }
   }

   //+------------------------------------------------------------------+
   //| True exactly once, on the call right after the gate becomes      |
   //| halted - lets the EA print/alert without spamming every tick.    |
   //+------------------------------------------------------------------+
   bool ConsumeJustHalted()
   {
      bool value = m_justHalted;
      m_justHalted = false;
      return(value);
   }

   void Reset()
   {
      m_consecutiveLosses = 0;
      m_barsSinceLoss     = -1;
      m_halted            = false;
      m_haltedReason      = "";
      m_justHalted        = false;
   }

   //+------------------------------------------------------------------+
   //| Looks up this EA's closing deals (DEAL_ENTRY_OUT) for `symbol`   |
   //| and `magic`, feeding each one's outcome into RecordOutcome().    |
   //| Tracks already-seen ticket numbers so a deal is never reported   |
   //| twice, however often this is called.                             |
   //+------------------------------------------------------------------+
   void CheckClosedTrades(const string symbol, const ulong magic)
   {
      if(!HistorySelect(0, TimeCurrent()))
         return;

      int total = HistoryDealsTotal();
      for(int i = 0; i < total; i++)
      {
         ulong ticket = HistoryDealGetTicket(i);
         if(ticket == 0 || AlreadySeen(ticket))
            continue;

         if(HistoryDealGetInteger(ticket, DEAL_MAGIC) != (long)magic)
            continue;
         if(HistoryDealGetString(ticket, DEAL_SYMBOL) != symbol)
            continue;
         if(HistoryDealGetInteger(ticket, DEAL_ENTRY) != DEAL_ENTRY_OUT)
            continue; // only closing deals represent a finished trade

         MarkSeen(ticket);
         double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
         RecordOutcome(profit < 0.0);
      }
   }
};

#endif // RISK_GATE_MQH
