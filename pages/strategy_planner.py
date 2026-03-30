# pages/06_Hybrid_Strategy_Guide.py
import streamlit as st
import pandas as pd
from datetime import datetime

# ─── Import your engine (adjust path if needed) ────────────────────────────────
# Assuming HybridStrategyEngine is in common/ or the same folder
from common.HybridStrategyEngine import HybridStrategyEngine

st.set_page_config(page_title="Hybrid Strategy Guide & Simulator", layout="wide")

# ─── Page Title & Hero Section ─────────────────────────────────────────────────
st.title("🚀 Hybrid Strategy: Compounding + Pyramiding")
st.markdown(
    """
    **Maximize returns on a ₹10 Lakh Nifty 500 portfolio**  
    by combining intelligent position sizing (**compounding**) with aggressive scaling into winners (**pyramiding**).
    """
)

# ─── Tabs: Documentation vs Simulator ──────────────────────────────────────────
tab_readme, tab_simulator, tab_notes = st.tabs([
    "📖 Strategy Guide",
    "🎮 Live Simulator",
    "⚠️ Important Notes & Tips"
])

# ────────────────────────────────────────────────────────────────────────────────
# TAB 1: Strategy Guide (Read Me)
# ────────────────────────────────────────────────────────────────────────────────
with tab_readme:
    st.header("How the Hybrid Model Works")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Core Components")

        st.markdown("""
        1. **Compounding Engine**  
           Every time a trade is closed (profit or loss), the realized PnL is added/subtracted from total equity.  
           → Future trades automatically use the **new larger (or smaller) capital base**.

        2. **Pyramiding (Scaling In)**  
           Instead of putting the full slot size at once, we scale in as the trade moves in our favor:

           | Layer     | Allocation | Trigger             | Purpose                          |
           |-----------|------------|---------------------|----------------------------------|
           | **Base**  | 50%        | Immediate entry     | Establish core position          |
           | **Layer 1** | 30%      | +10% from entry     | Add conviction on strength       |
           | **Layer 2** | 20%      | +20% from entry     | Maximize winner, reduce risk     |

        3. **Risk Controls**  
           - Max **8 concurrent stocks** (≈12.5% capital per slot)  
           - Initial **Stop Loss**: 8% below entry  
           - After Layer 1: SL moves to **breakeven** (+0–2%)  
           - After Layer 2: SL moves to **+10%** (locking in gains)
        """)

    with col2:
        st.subheader("Portfolio Math Example")
        st.info("""
        Starting capital: **₹10,00,000**  
        Slots: **8**  
        → Max per stock: **₹1,25,000**

        After a big winner (+₹15,50,000 profit):  
        New equity → **₹25,50,000**  
        New slot size → **₹3,18,750**  
        → Next trade base entry becomes **much larger**
        """)

    st.divider()

    st.subheader("How to Use in Live Trading")

    st.code("""
# 1. Initialize once (or on app restart)
engine = HybridStrategyEngine(initial_capital=your_zerodha_balance)

# 2. When you get a new signal
plan = engine.generate_trade_plan("TRENT", current_price=4850)

# 3. Place orders
# - Buy Base layer immediately
# - Set GTT buy orders for Layer 1 & Layer 2
# - Set initial SL GTT

# 4. When trade is fully closed
engine.on_trade_close(realized_profit_or_loss)
    """, language="python")

# ────────────────────────────────────────────────────────────────────────────────
# TAB 2: Live Simulator
# ────────────────────────────────────────────────────────────────────────────────
with tab_simulator:
    st.header("🎮 Interactive Trade Simulator")

    st.info("Play with different capital sizes and entry prices to see how the pyramid plan and compounding behave.")

    # ── Inputs ────────────────────────────────────────────────────────────────
    col_cap, col_price, col_slots = st.columns([2, 2, 1])

    with col_cap:
        capital = st.number_input(
            "Portfolio Equity (₹)",
            min_value=100000,
            max_value=10000000,
            value=1000000,
            step=50000,
            format="%d"
        )

    with col_price:
        entry_price = st.number_input(
            "Entry Price (₹)",
            min_value=10.0,
            max_value=20000.0,
            value=1000.0,
            step=5.0,
            format="%.2f"
        )

    with col_slots:
        num_slots = st.number_input(
            "Max Slots",
            min_value=4,
            max_value=12,
            value=8,
            step=1
        )

    symbol_sim = st.text_input("Symbol (for display)", value="SIMULATED", max_chars=12)

    if st.button("Generate Trade Plan & Simulate", type="primary"):
        with st.spinner("Calculating pyramid plan..."):
            engine = HybridStrategyEngine(initial_capital=capital, num_slots=num_slots)
            plan = engine.generate_trade_plan(symbol_sim, entry_price)

        st.success("Trade Plan Generated!")

        # ── Display Plan in nice table ────────────────────────────────────────
        layers = plan['layers']

        data = {
            "Layer": ["Base", "Layer 1 (+10%)", "Layer 2 (+20%)"],
            "Trigger Price": [
                f"₹{layers['Base']['trigger_price']:,.2f}",
                f"₹{layers['Layer1']['trigger_price']:,.2f}",
                f"₹{layers['Layer2']['trigger_price']:,.2f}"
            ],
            "Allocation %": ["50%", "30%", "20%"],
            "Quantity": [
                layers['Base']['qty'],
                layers['Layer1']['qty'],
                layers['Layer2']['qty']
            ],
            "Investment (₹)": [
                round(capital / num_slots * 0.50, 2),
                round(capital / num_slots * 0.30, 2),
                round(capital / num_slots * 0.20, 2)
            ]
        }

        df_plan = pd.DataFrame(data)

        st.subheader(f"Trade Plan for {plan['symbol']} @ ₹{entry_price:,.2f}")
        st.dataframe(
            df_plan.style.format({
                "Investment (₹)": "₹{:,.2f}",
                "Trigger Price": "{}"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "Initial Stop Loss",
            f"₹{plan['stop_loss']:,.2f}",
            delta=f"-{round((entry_price - plan['stop_loss'])/entry_price*100, 1)}%",
            delta_color="inverse"
        )

        # ── Compounding preview after big win ────────────────────────────────
        st.subheader("What happens after a big winner?")
        profit_example = st.slider(
            "Simulate realized profit after this trade (₹)",
            0,
            5000000,
            1550000,
            step=50000
        )

        if profit_example > 0:
            new_equity = capital + profit_example
            new_slot = new_equity / num_slots
            st.info(f"""
            **After closing with +₹{profit_example:,.0f} profit**  
            → New Portfolio Equity: **₹{new_equity:,.0f}**  
            → New Slot Size: **₹{new_slot:,.0f}**  
            → New Base Entry (50%): **₹{new_slot*0.5:,.0f}**
            """)

# ────────────────────────────────────────────────────────────────────────────────
# TAB 3: Important Notes
# ────────────────────────────────────────────────────────────────────────────────
with tab_notes:
    st.header("⚠️ Critical Reminders")

    st.warning("""
    **Never average down**  
    This system **only adds to winners**. Never add to losing positions.

    **Use GTT orders**  
    Automate Layer 1 & Layer 2 entries + trailing SL using Zerodha GTTs.

    **Margin & Leverage**  
    For large orders, consider buying far OTM options (₹2–5) as hedge to reduce margin requirement.

    **Risk per slot**  
    Even though max 12.5% per stock, pyramiding can take total exposure higher temporarily. Monitor closely.

    **Not financial advice**  
    This is an educational simulation. Past performance ≠ future results. Use at your own risk.
    """)

    st.subheader("Recommended Next Steps")
    st.markdown("""
    1. Update `initial_capital` to your actual Zerodha equity  
    2. Connect to Kite API for live prices & order placement  
    3. Backtest this logic on historical signals  
    4. Start paper trading with small real capital
    """)

st.caption(f"Hybrid Strategy Engine • Last updated: {datetime.now().strftime('%d %b %Y %H:%M')}")