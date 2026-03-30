import pandas as pd
from datetime import datetime


class HybridStrategyEngine:
    def __init__(self, initial_capital=1000000, num_slots=8):
        """
        initial_capital: Total starting amount (10L).
        num_slots: Maximum number of concurrent stocks (8).
        """
        self.total_equity = initial_capital
        self.num_slots = num_slots
        # State to track active trades and their current pyramid layer
        self.active_trades = {}

    def get_compounded_slot_size(self):
        """Calculates the total budget for the next NEW trade (Compounding)."""
        return self.total_equity / self.num_slots

    def generate_trade_plan(self, symbol, entry_price):
        """
        Calculates the 3-stage entry plan for a specific stock (Pyramiding).
        Uses a 50%-30%-20% allocation model.
        """
        total_budget = self.get_compounded_slot_size()

        plan = {
            'symbol': symbol,
            'status': 'OPENING',
            'total_budget': total_budget,
            'layers': {
                'Base': {
                    'allocation': 0.50,  # 50% of slot
                    'trigger_price': entry_price,
                    'qty': int((total_budget * 0.50) / entry_price),
                    'executed': False
                },
                'Layer1': {
                    'allocation': 0.30,  # 30% of slot
                    'trigger_price': round(entry_price * 1.10, 2),  # +10% move
                    'qty': int((total_budget * 0.30) / (entry_price * 1.10)),
                    'executed': False
                },
                'Layer2': {
                    'allocation': 0.20,  # 20% of slot
                    'trigger_price': round(entry_price * 1.20, 2),  # +20% move
                    'qty': int((total_budget * 0.20) / (entry_price * 1.20)),
                    'executed': False
                }
            },
            'stop_loss': round(entry_price * 0.92, 2)  # Initial 8% SL
        }
        return plan

    def on_trade_close(self, realized_pnl):
        """
        Updates global equity after a trade closes (Compounding).
        """
        self.total_equity += realized_pnl
        print(f"--- Portfolio Re-Compounded ---")
        print(f"New Equity: ₹{self.total_equity:,.2f}")
        print(f"New Base Entry Size: ₹{self.get_compounded_slot_size() * 0.5:,.2f}")


# --- EXECUTION SIMULATION ---

# 1. Initialize with 10L
engine = HybridStrategyEngine(initial_capital=1000000)

# 2. Received Signal for APARINDS at 1000
new_trade = engine.generate_trade_plan("APARINDS", 1000)

print(f"Executing Base Entry for {new_trade['symbol']}...")
print(f"Buy Qty: {new_trade['layers']['Base']['qty']} | Initial SL: {new_trade['stop_loss']}")

# 3. If APARINDS wins (simulating your 1245% gain on a 1.25L slot)
# Realized profit would be approx 15.5L
engine.on_trade_close(1550000)

# 4. Next signal will now have a much larger size automatically
next_trade = engine.generate_trade_plan("TRENT", 5000)
print(f"\n--- Next Trade Compounded ---")
print(f"TRENT Base Entry Qty: {next_trade['layers']['Base']['qty']} (reflects larger equity)")