class CompoundingEngine:
    def __init__(self, initial_capital=1000000, num_slots=8):
        self.num_slots = num_slots
        # In production, this would be: kite.margins()['equity']['net']
        self.current_equity = initial_capital

    def update_equity(self, realized_pnl):
        """Call this function every time a trade is closed."""
        self.current_equity += realized_pnl
        print(f"New Portfolio Equity: ₹{self.current_equity:,.2f}")

    def get_current_slot_sizes(self):
        """Calculates the new investment for the next signal."""
        total_slot = self.current_equity / self.num_slots
        return {
            "Full_Slot": round(total_slot, 2),
            "Base_Entry": round(total_slot * 0.50, 2),
            "Pyramid_1": round(total_slot * 0.30, 2),
            "Pyramid_2": round(total_slot * 0.20, 2)
        }

# --- Automation Integration ---
engine = CompoundingEngine(initial_capital=1000000)

# Simulate closing a winning trade like APARINDS (+1245%)
# If we had a full slot of 1.25L, profit would be ~15.5L
engine.update_equity(1550000)

new_sizes = engine.get_current_slot_sizes()
print(f"Next Trade Base Entry: ₹{new_sizes['Base_Entry']:,.2f}")