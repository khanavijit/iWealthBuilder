Summary of Running StateComponentLocation
Run CommandBackend (FastAPI)Terminal 1  uvicorn app.main:app --reload
Frontend (Streamlit)Terminal 2  streamlit run iwealth_builder_app.py
Application URLWeb Browser  http://localhost:8501
API Base URLBackend Server  http://127.0.0.1:8000



🚀 Hybrid Strategy: Compounding & Pyramiding
This system is designed for a ₹10 Lakh Nifty 500 portfolio to maximize profits using the Hybrid Model:

Compounding: Reinvests portfolio gains to increase the size of future trades.

Pyramiding: Scales into winning trades as they move in your favor.

📋 Strategy Rules
Slots: Max 8 concurrent stocks (12.5% allocation per slot).

Entry Model: 50-30-20 Pyramid.

Base (50%): Immediate entry on signal.

Layer 1 (+30%): Add when price gains +10%.

Layer 2 (+20%): Add when price gains +20%.

Risk Management: * Initial Stop Loss at 8%.

Move Stop Loss to Break-even when Layer 1 is added.

Move Stop Loss to +10% when Layer 2 is added.

💻 How to Use the Program
Initialization: Update the initial_capital in the script to your current Zerodha account balance.

Python

engine = HybridStrategyEngine(initial_capital=1000000)
Generating a Trade Plan: When you receive a signal, run generate_trade_plan. It will tell you exactly how many shares to buy for the Base layer and the GTT triggers for the Pyramid layers.

Python

plan = engine.generate_trade_plan("SYMBOL", price)
Closing a Trade: Whenever you exit a trade, pass the Realized PnL (Profit or Loss) to the engine. This automatically "Re-compounds" your capital so your next trade uses the new balance.

Python

engine.on_trade_close(profit_amount)
⚠️ Important Notes
Never Average Down: Only add to positions that are showing a profit.

Margin Hedges: Buy a far OTM option (₹2-5) before selling or buying large lots to reduce margin requirements and boost ROI.

Automation: Use Zerodha GTT orders to automate the Layer 1 and Layer 2 entries so you don't have to watch the screen all day.