import pandas as pd

class PositionManager:
    def __init__(self, total_capital=1000000, risk_per_trade_pct=1.5):
        self.total_capital = total_capital
        self.max_allocation_per_stock = total_capital * 0.125  # 12.5% (8 Slots)
        self.risk_per_trade_in_rupees = total_capital * (risk_per_trade_pct / 100)

    def calculate_pyramid_plan(self, symbol, entry_price):
        """
        Calculates a 3-layer pyramid for a single trade.
        """
        # Define Layer Weights (Total must be 100% of the max allocation)
        # We use a standard 50-30-20 Pyramid
        base_amt = self.max_allocation_per_stock * 0.50   # 6.25% of Total Cap
        layer1_amt = self.max_allocation_per_stock * 0.30 # 3.75% of Total Cap
        layer2_amt = self.max_allocation_per_stock * 0.20 # 2.50% of Total Cap

        plan = {
            "Symbol": symbol,
            "Base_Entry": {
                "Price": entry_price,
                "Quantity": int(base_amt / entry_price),
                "Investment": round(base_amt, 2),
                "Initial_SL": round(entry_price * 0.92, 2)  # 8% Stop Loss
            },
            "Layer_1_Add": {
                "Trigger_Price": round(entry_price * 1.10, 2), # Add at +10%
                "Quantity": int(layer1_amt / (entry_price * 1.10)),
                "New_Trailing_SL": round(entry_price * 1.02, 2) # Move SL to Cost+2%
            },
            "Layer_2_Add": {
                "Trigger_Price": round(entry_price * 1.20, 2), # Add at +20%
                "Quantity": int(layer2_amt / (entry_price * 1.20)),
                "New_Trailing_SL": round(entry_price * 1.10, 2) # Move SL to +10%
            }
        }
        return plan

# --- Usage Example ---
manager = PositionManager(total_capital=1000000)
trade_plan = manager.calculate_pyramid_plan("APARINDS", 1000)

print(f"--- Trade Plan for {trade_plan['Symbol']} ---")
print(f"1. Base Buy: {trade_plan['Base_Entry']['Quantity']} shares at ₹{trade_plan['Base_Entry']['Price']}")
print(f"2. Pyramid 1: Add {trade_plan['Layer_1_Add']['Quantity']} shares if price hits ₹{trade_plan['Layer_1_Add']['Trigger_Price']} SL ₹{trade_plan['Layer_1_Add']['New_Trailing_SL']}")
print(f"3. Pyramid 2: Add {trade_plan['Layer_2_Add']['Quantity']} shares if price hits ₹{trade_plan['Layer_2_Add']['Trigger_Price']} SL ₹{trade_plan['Layer_1_Add']['New_Trailing_SL']}")