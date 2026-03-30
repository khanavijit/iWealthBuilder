
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from Constants import GEMINI_API_KEY, INDICATOR_API_HOST, INDICATOR_API_USERNAME, INDICATOR_API_PASSWORD, MINERVINI_CHART_DAYS_AGO
from common.IndicatorApi import IndicatorApi
from common.api_utils import fetch_user_investments, add_new_transaction, search_catalog_items, add_catalog_item, fetch_catalog, add_user_holding, fetch_open_signals
from common.minervini import Minervini
from gemini_helper import get_gemini_suggestion
from testGemini import add_user_investment
api = IndicatorApi(INDICATOR_API_USERNAME, INDICATOR_API_PASSWORD, host=INDICATOR_API_HOST)
# --- Configuration & Global Variables ---
# API_BASE_URL = "http://127.0.0.1:8000"
st.set_page_config(layout="wide", page_title="iWealthBuilder Dashboard")

# Global/Constant Allocation Profiles for Smart Allocation Tab
# NOTE: These keys must match the 'asset_category' Enum in your backend models
ALLOCATION_PROFILES = {
    "Conservative (Low Risk)": {
        "STOCK": 20, "MF": 10, "FD": 35, "PPF": 25, "DERIVATIVES": 0
    },
    "Moderate (Balanced)": {
        "STOCK": 45, "MF": 15, "FD": 20, "PPF": 10, "DERIVATIVES": 10
    },
    "Aggressive (High Risk)": {
        "STOCK": 60, "MF": 20, "FD": 5, "PPF": 5, "DERIVATIVES": 10
    },
    "High Growth (Very High Risk)": {
        "STOCK": 70, "DERIVATIVES": 10, "MF": 15, "FD": 0, "PPF": 5
    }
}



# --- Render Functions ---

def render_kpi_card(title: str, value: Any, delta: Optional[Any] = None, help_text: str = ""):
    """Renders a standard KPI metric card."""
    with st.container():
        st.metric(label=title, value=value, delta=delta, help=help_text)


def render_dashboard_details(portfolio_data: Dict[str, Any]):
    st.header("Portfolio Overview")

    # --- UPDATED KPI SECTION ---
    # Split P&L into clearer metrics as requested

    total_value = f"{portfolio_data.get('total_market_value', 0):,.2f} INR"
    total_invested = portfolio_data.get('total_invested_capital', 0)
    total_withdrawn = portfolio_data.get('total_withdrawn_capital', 0)
    realized_pnl_val = portfolio_data.get('total_realized_pnl', 0)
    unrealized_pnl_val = portfolio_data.get('total_unrealized_pnl', 0)

    # Calculate cost basis of *remaining* assets for unrealized P&L %
    cost_basis_remaining = total_invested - total_withdrawn - realized_pnl_val
    unrealized_pct_str = "0.00%"
    if cost_basis_remaining > 0:
        unrealized_pct = (unrealized_pnl_val / cost_basis_remaining) * 100
        unrealized_pct_str = f"{unrealized_pct:.2f}%"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_kpi_card("Total Market Value", total_value, help_text="Current total value of all active holdings.")
    with col2:
        render_kpi_card(
            "Unrealized P&L",
            f"{unrealized_pnl_val:,.2f} INR",
            delta=unrealized_pct_str,
            help_text="Current paper profit or loss on active holdings. Delta is vs. cost basis of remaining assets."
        )
    with col3:
        render_kpi_card(
            "Total Invested",
            f"{total_invested:,.2f} INR",
            help_text="Total cash deposits across all investments, ever."
        )
    with col4:
        render_kpi_card(
            "Total Withdrawn",
            f"{total_withdrawn:,.2f} INR",
            help_text="Total cash withdrawals across all investments, ever."
        )
    with col5:
        render_kpi_card(
            "Realized P&L",
            f"{realized_pnl_val:,.2f} INR",
            help_text="Total profit or loss from completed sales (closed positions)."
        )
    # --- END OF UPDATED KPI SECTION ---

    st.subheader("Asset Allocation Breakdown")
    investments = portfolio_data.get("investments", [])

    if investments:
        df_inv = pd.DataFrame(investments)
        df_inv['current_market_value'] = df_inv['current_market_value'].astype(float)

        # Calculate allocation by category (this field is now in the summary)
        allocation = df_inv.groupby('asset_category')['current_market_value'].sum().reset_index()
        allocation.columns = ['Category', 'Value']

        total_portfolio_value = allocation['Value'].sum()
        if total_portfolio_value > 0:
            allocation['Percentage'] = (allocation['Value'] / total_portfolio_value) * 100
            allocation['Label'] = allocation.apply(lambda row: f"{row['Category']} ({row['Percentage']:.1f}%)", axis=1)

            col_chart, col_data = st.columns([1, 1])

            with col_chart:
                fig = px.pie(
                    allocation,
                    values='Value',
                    names='Label',
                    title='Portfolio Allocation by Category',
                    hole=.3,
                    height=400
                )
                fig.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
                fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)

            with col_data:
                st.subheader("Asset Details")
                display_cols = ['name', 'symbol', 'risk_category', 'asset_category', 'current_market_value', 'unrealized_pnl']
                df_display = df_inv[display_cols].copy()
                df_display.columns = ['Asset Name', 'Symbol', 'Risk', 'Type', 'Current Value (INR)', 'Unrealized PnL']

                df_display['Current Value (INR)'] = df_display['Current Value (INR)'].map('{:,.2f}'.format)
                df_display['Unrealized PnL'] = df_display['Unrealized PnL'].map('{:,.2f}'.format)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No market value in portfolio to display allocation.")
    else:
        st.warning("No assets to display. Please add a new asset in the 'Add New Asset' tab.")



# --- NEW COMBINED FUNCTION ---
def render_ai_allocation_planner(portfolio_data: Dict[str, Any]):
    st.header("🤖 Smart Allocation & AI Advisor")
    st.info("Use this tab to plan new investments based on your risk profile, rebalance your portfolio, or get AI-driven market analysis.")

    # --- Shared Profile Selector ---
    col_profile, col_space = st.columns([1, 3])
    with col_profile:
        selected_profile = st.selectbox(
            "Select Your Risk Profile",
            options=list(ALLOCATION_PROFILES.keys()),
            key='gemini_profile',
            help="This profile controls both new capital allocation and the rebalancing planner."
        )
    target_allocation = ALLOCATION_PROFILES[selected_profile]

    # --- Feature 1: Allocate New Capital ---
    st.markdown("---")
    st.subheader("1. Allocate New Capital")

    # Get user's current investments to populate dropdowns
    user_investments = fetch_user_investments()
    investment_map_by_category = {}
    for inv in user_investments:
        category = inv['catalog']['asset_category']
        if category not in investment_map_by_category:
            investment_map_by_category[category] = {}
        # Use a clear display name but map it to the all-important UserInvestment ID
        display_name = f"{inv['nickname']} ({inv['catalog']['symbol']}) - [ID: {inv['id']}]"
        investment_map_by_category[category][display_name] = inv['id']

    with st.form("new_allocation_form"):
        new_capital = st.number_input("Amount to Invest (INR)", min_value=0.0, step=1000.0)

        allocation_plan = []
        if new_capital > 0:
            st.markdown(f"**Investment Plan for {new_capital:,.2f} INR ({selected_profile})**")

            # Calculate the plan
            for category, pct in target_allocation.items():
                if pct > 0:
                    amount = new_capital * (pct / 100)
                    allocation_plan.append({
                        "Category": category,
                        "Amount": amount,
                        "Target %": pct,
                    })

            df_plan = pd.DataFrame(allocation_plan)
            df_plan['Amount'] = df_plan['Amount'].map('{:,.2f}'.format)
            st.dataframe(df_plan, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Select Assets for Allocation")

            # This dict will hold the final plan: {investment_id: amount}
            allocation_payload = {}
            has_valid_assets = False

            for item in allocation_plan:
                category = item["Category"]
                amount = item["Amount"]

                # Find available assets in portfolio for this category
                available_assets = investment_map_by_category.get(category, {})

                if not available_assets:
                    st.warning(f"**{category}**: No assets found in your portfolio for this category. Please add one in the 'Add/Manage Assets' tab.")
                else:
                    has_valid_assets = True
                    # Create a dropdown for the user to pick which asset gets the funds
                    display_choice = st.selectbox(
                        f"Select asset for **{category}** ({amount} INR)",
                        options=list(available_assets.keys()),
                        key=f"asset_choice_{category}"
                    )
                    # Get the UserInvestment ID from the display name
                    inv_id = available_assets[display_choice]
                    # Store the ID and the *numeric* amount
                    allocation_payload[inv_id] = item["Amount"]

        submitted = st.form_submit_button("Execute Allocation Plan (Batch Deposits)")

        if submitted and new_capital > 0:
            if not allocation_payload:
                st.error("No assets were selected or available for allocation. Transaction cancelled.")
            else:
                with st.spinner("Processing transactions..."):
                    success_count = 0
                    fail_count = 0
                    for inv_id, amount in allocation_payload.items():
                        tx_data = {
                            "type": "DEPOSIT",
                            "date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "cash_amount": amount,
                            "units": None,  # API can handle nulls for non-unit-based
                            "price_per_unit": None
                        }
                        result = add_new_transaction(inv_id, tx_data)
                        if result:
                            success_count += 1
                        else:
                            fail_count += 1

                    st.success(f"Successfully processed {success_count} transactions.")
                    if fail_count > 0:
                        st.error(f"{fail_count} transactions failed. Check API logs.")

                    st.cache_data.clear()
                    st.rerun()

    # --- Feature 2: Rebalancing Planner ---
    st.markdown("---")
    st.subheader("2. Rebalancing Planner")

    target_df = pd.DataFrame.from_dict(target_allocation, orient='index', columns=['Target (%)'])
    st.subheader(f"Target Allocation ({selected_profile} Profile)")
    st.dataframe(target_df.T, use_container_width=True)

    st.subheader("Current vs. Target Breakdown")
    investments = portfolio_data.get("investments", [])
    if investments:
        df_inv = pd.DataFrame(investments)
        df_inv['current_market_value'] = df_inv['current_market_value'].astype(float)

        current_allocation_abs = df_inv.groupby('asset_category')['current_market_value'].sum()
        total_value = current_allocation_abs.sum()

        if total_value > 0:
            current_allocation_pct = (current_allocation_abs / total_value * 100).round(1)
            comparison_data = []
            all_categories = set(target_allocation.keys()) | set(current_allocation_abs.index)

            for category in sorted(list(all_categories)):
                target_pct = target_allocation.get(category, 0.0)
                current_pct = current_allocation_pct.get(category, 0.0)
                current_value = current_allocation_abs.get(category, 0.0)
                diff_pct = current_pct - target_pct
                target_value = total_value * (target_pct / 100)
                rebalance_amount = target_value - current_value

                comparison_data.append({
                    'Category': category,
                    'Current Value (INR)': current_value,
                    'Current (%)': current_pct,
                    'Target (%)': target_pct,
                    'Difference (Current - Target)': f"{diff_pct:.1f}%",
                    'Rebalance Action (INR)': rebalance_amount
                })

            df_comparison = pd.DataFrame(comparison_data)

            def color_diff(val):
                if isinstance(val, str): val = float(val.replace('%', ''))
                color = 'red' if val > 2 else 'green' if val < -2 else ''
                return f'color: {color}'

            df_comparison['Current Value (INR)'] = df_comparison['Current Value (INR)'].map('{:,.2f}'.format)
            df_comparison['Rebalance Action (INR)'] = df_comparison['Rebalance Action (INR)'].map(lambda x: f"{x:,.2f} {'(BUY)' if x > 0 else '(SELL)' if x < 0 else '(HOLD)'}")

            st.dataframe(
                df_comparison.style.applymap(
                    color_diff,
                    subset=['Difference (Current - Target)']
                ),
                use_container_width=True,
                hide_index=True
            )

            # Add instructional note as requested
            st.info(
                "**How to act on this plan:**\n"
                "1.  **For (BUY) actions:** Use the 'Allocate New Capital' tool (Section 1, above) to add funds to your underweight categories.\n"
                "2.  **For (SELL) actions:** Go to the 'SIP Management' tab and log a 'WITHDRAWAL' transaction for the specified amount on an asset in that category. You will need to provide the units and price for the sale."
            )
        else:
            st.info("No market value in portfolio to calculate allocation.")
    else:
        st.warning("Cannot calculate allocation. Please add investments first.")

    # --- Feature 3: AI Advisor ---
    st.markdown("---")
    st.subheader("3. AI Market Analysis")

    st.info("""
    This section demonstrates how you could integrate the Gemini API for market analysis.
    The logic here is a placeholder. You would need to implement the call to the
    Gemini API using your own API key and prompt engineering.
    """)

    market_prompt = st.text_area(
        "Market Analysis Prompt",
        "Analyze the current market sentiment for the Indian IT sector (e.g., TCS, Infosys) and the Indian Banking sector (e.g., HDFC, ICICI) for the next quarter. Provide a brief summary and a recommended allocation adjustment (e.g., 'Increase banking exposure', 'Hold IT').",
        height=150
    )

    if st.button("Generate AI Investment Suggestion", type="primary"):
        if not GEMINI_API_KEY:
            st.error("Please configure the `GEMINI_API_KEY` in the application file to run the AI analysis.")
            return

        with st.spinner(f"Consulting iWealthAI on the {st.session_state['gemini_profile']} profile..."):
            ai_suggestion = get_gemini_suggestion(
                st.session_state['gemini_profile'],
                portfolio_data
            )
            st.markdown(ai_suggestion)

    # if st.button("Run AI Market Analysis"):
    #     with st.spinner("Calling Gemini API for analysis... (Mock delay)"):
    #         # --- This is where you would call your Gemini API function ---
    #
    #         def fetch_gemini_recommendation(prompt: str) -> str:
    #             # 1. Setup Gemini API headers/payload
    #             # 2. Make POST request
    #             # 3. Parse response
    #             # 4. Return formatted markdown string
    #             time.sleep(2) # Mocking API call
    #             return f"**Analysis based on your prompt:**\n\n* **IT Sector:** Sentiment appears cautious... \n* **Banking Sector:** Strong domestic credit growth... \n\n**Recommendation:**\n\nConsider holding IT positions but prioritize new capital towards Banking..."
    #
    #         recommendation = fetch_gemini_recommendation(market_prompt)
    #
    #
    #         # Mocking the response for this demo:
    #         # time.sleep(2)
    #         recommendation = f"**Analysis based on your prompt:**\n\n* **IT Sector:** Sentiment appears cautious due to global headwinds. Valuations are reasonable, but near-term growth is uncertain.\n* **Banking Sector:** Strong domestic credit growth and robust balance sheets provide a positive outlook. ...\n\n**Recommendation:**\n\nConsider holding current IT positions but prioritize new capital allocation towards the Banking sector. A slight overweight on Banking (e.g., +5% to 10% in your 'Smart Allocation' profile) seems justified for the next quarter."
    #
    #         st.subheader("Gemini API Recommendation")
    #         st.markdown(recommendation)
    #
    #         st.warning("This is mock data. To implement this, replace the placeholder logic with a real API call to the Gemini API.")


def render_sip_management():
    st.header("Systematic Investment Plan (SIP) Manager")

    # Fetch the full list of user investments (UserInvestmentReadWithCatalog)
    user_investments = fetch_user_investments()

    if not user_investments:
        st.warning("No investments found in your portfolio. Please add an asset first.")
        return

    st.subheader("My SIP Configurations")

    # --- This is the new table you requested ---
    sip_data = []
    for inv in user_investments:
        sip_data.append({
            "ID": inv['id'],
            "Asset Name": inv['catalog']['name'],
            "Symbol": inv['catalog']['symbol'],
            "My Nickname": inv['nickname'],
            "SIP Frequency": inv['sip_frequency']
        })

    df_sip_config = pd.DataFrame(sip_data)
    st.dataframe(df_sip_config, use_container_width=True, hide_index=True)
    # --- End of new table ---

    st.markdown("---")
    st.subheader("Log Manual Transaction (SIP / Buy / Sell)")

    # Create a mapping of display name to ID for the form
    inv_options_map = {
        f"{inv['nickname']} ({inv['catalog']['symbol']}) - [ID: {inv['id']}]": inv['id']
        for inv in user_investments
    }
    if not inv_options_map:
        st.info("No assets in portfolio to transact against.")
        return

    with st.form("sip_contribution_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            selected_inv_display = st.selectbox(
                "Select Asset",
                options=list(inv_options_map.keys()),
                key='sip_asset_name'
            )
        inv_id = inv_options_map[selected_inv_display]

        with col2:
            tx_type = st.selectbox("Transaction Type", ["DEPOSIT", "WITHDRAWAL"])
        with col3:
            tx_date = st.date_input("Transaction Date", value=datetime.now(), key='sip_date')

        st.subheader("Transaction Details")
        t_col1, t_col2, t_col3 = st.columns(3)

        with t_col1:
            cash_amount = st.number_input("Cash Amount (INR)", min_value=0.01, step=50.0, format="%.2f", key='sip_amount')
        with t_col2:
            units = st.number_input("Units (Optional for Deposit)", min_value=0.0, step=1.0, format="%.4f", key='sip_units')
        with t_col3:
            price_per_unit = st.number_input("Price Per Unit (Optional for Deposit)", min_value=0.0, step=0.01, format="%.4f", key='sip_price')

        st.info("For WITHDRAWALs, 'Units' and 'Price Per Unit' are required by the API to calculate P&L.")

        submitted = st.form_submit_button(f"Log {tx_type} Transaction")

        if submitted:
            transaction_data = {
                "type": tx_type,
                "date": tx_date.strftime("%Y-%m-%dT%H:%M:%S"),  # Send as datetime string
                "cash_amount": cash_amount,
                "units": units if units > 0 else None,
                "price_per_unit": price_per_unit if price_per_unit > 0 else None,
            }

            result = add_new_transaction(inv_id, transaction_data)

            if result:
                st.success(f"{tx_type} transaction of {cash_amount:,.2f} INR logged for {selected_inv_display}!")
                st.cache_data.clear()  # Clear all cache
                st.rerun()


def _search_catalog():
    """Handles the catalog search triggered by text input change."""
    search_input = st.session_state.search_asset_input

    # Reset selection every time a search is performed
    st.session_state['selected_catalog_id'] = None
    st.session_state['selected_catalog_name'] = ""

    if len(search_input) >= 3:
        # Perform search and update results
        st.session_state['search_query'] = search_input
        st.session_state['search_results'] = search_catalog_items(search_input)
    else:
        # Clear results if input is too short
        st.session_state['search_results'] = []


# --- End of Helper function ---
def render_add_manage_assets():
    """Renders the interface for adding new assets (Catalog) and holdings (User Investment)."""
    st.header("Add/Manage Assets")

    tab_holding, tab_catalog = st.tabs(["Add Investment Holding", "Create New Asset Type (Catalog)"])

    # --------------------------------------------------------
    # TAB 1: Add Investment Holding (UserInvestment)
    # --------------------------------------------------------
    with tab_holding:
        st.subheader("1. Link an Asset from the Catalog to Your Portfolio")
        st.markdown("**Search for a stock, MF, or FD** (e.g., 'RIL', 'Quant', 'HDFC'). Minimum 3 characters required. The search is automatic as you type.")

        # State initialization (re-confirmed for clarity)
        if 'search_query' not in st.session_state:
            st.session_state['search_query'] = ""
        if 'search_results' not in st.session_state:
            st.session_state['search_results'] = []
        if 'selected_catalog_id' not in st.session_state:
            st.session_state['selected_catalog_id'] = None
        if 'selected_catalog_name' not in st.session_state:
            st.session_state['selected_catalog_name'] = ""

        # --- START OF SEARCH LOGIC ---

        # Search input with on_change for key press search
        # with st.form("search_form_isolate", clear_on_submit=False):
        #     st.text_input(
        #         "Search Asset Name or Symbol",
        #         value=st.session_state['search_query'],
        #         key="search_asset_input",
        #         placeholder="Enter 3+ characters to search...",
        #         on_change=_search_catalog,  # Call helper function on change
        #     )
        #
        #     st.form_submit_button("Search Trigger", disabled=True, use_container_width=False)
        # with st.form("search_form_isolate", clear_on_submit=False):
        search_input = st.text_input(
            "Search Asset Name or Symbol",
            value=st.session_state.get('search_asset_input', ''),
            key="search_asset_input",
            placeholder="Enter 3+ characters to search..."
        )

        # Automatically trigger search when 3+ letters are typed
        if len(search_input) >= 3:
            _search_catalog()

        # Display Search Results and Selection Logic
        catalog_map = {}
        if st.session_state['search_results']:

            # Map for display in selectbox
            options = [
                f"{item['name']} ({item['symbol']} - {item['asset_category']})"
                for item in st.session_state['search_results']
            ]

            # Map back to ID
            for item in st.session_state['search_results']:
                key = f"{item['name']} ({item['symbol']} - {item['asset_category']})"
                catalog_map[key] = item['id']

            # Use st.radio for a clear selection interface
            st.subheader("Search Results")
            selected_option = st.radio(
                "Select the asset you wish to add:",
                options,
                key="selected_catalog_option"
            )

            # Update session state with the actual ID
            if selected_option:
                st.session_state['selected_catalog_id'] = catalog_map.get(selected_option)
                st.session_state['selected_catalog_name'] = selected_option

        elif st.session_state['search_query'] and len(st.session_state['search_query']) >= 3:
            st.info(f"No results found for '{st.session_state['search_query']}'. Try a different term or create a new asset type.")

        elif len(st.session_state['search_query']) < 3 and st.session_state['search_query'] != "":
            st.warning("Keep typing... Minimum 3 characters required to search.")

        # --- END OF SEARCH LOGIC ---

        st.markdown("---")

        # Holding Creation Form (Only visible if an item is selected)
        if st.session_state['selected_catalog_id']:

            # Isolate the clean name (everything before the first '(') for the nickname
            full_name = st.session_state['selected_catalog_name']
            clean_name = full_name.split(' (')[0] if ' (' in full_name else full_name

            st.subheader(f"2. Add Selected Asset as a New Holding")
            st.info(f"Adding: **{st.session_state['selected_catalog_name']}**")

            if 'clear_add_holding_form' not in st.session_state:
                st.session_state['clear_add_holding_form'] = False

            with st.form("add_holding_form"):
                nickname = st.text_input(
                    "Holding Nickname (e.g., 'My HDFC FD')",
                    value=clean_name,
                    key="new_holding_nickname"
                )

                sip_frequency = st.selectbox(
                    "Default SIP/Investment Frequency",
                    ['NONE', 'MONTHLY', 'YEARLY', 'WEEKLY'],
                    key="new_holding_sip"
                )

                submit_holding = st.form_submit_button("Add New Investment Holding")

            if submit_holding:
                if not nickname:
                    st.error("Please provide a nickname for this holding.")
                else:
                    user_inv_data = {
                        "catalog_id": st.session_state['selected_catalog_id'],
                        "nickname": nickname,
                        "sip_frequency": sip_frequency
                    }

                    result = add_user_investment(user_inv_data)

                    if result:
                        st.success(f"Successfully added holding '{nickname}' (ID: {result['id']})!")

                        # Clear relevant session state
                        st.session_state['search_query'] = ""
                        st.session_state['search_results'] = []
                        st.session_state['selected_catalog_id'] = None
                        st.session_state['selected_catalog_name'] = ""

                        # Set flag to clear form defaults next render
                        st.session_state.clear_add_holding_form = True

    # --------------------------------------------------------
    # TAB 2: Create New Asset Type (InvestmentCatalog)
    # --------------------------------------------------------
    with tab_catalog:
        st.subheader("2. Create a New Asset Type in the Catalog")
        st.markdown("Use this only if the asset type (e.g., 'New Crypto Token' or 'New Local Bond') doesn't exist.")

        with st.form("add_catalog_form"):
            name = st.text_input("Asset Name (e.g., Tesla Stock, New Small Cap Fund)", key="catalog_name")
            symbol = st.text_input("Ticker/Symbol (e.g., TSLA, LSCF)", key="catalog_symbol")

            col_a, col_b = st.columns(2)

            with col_a:
                asset_category = st.selectbox(
                    "Asset Category",
                    ['STOCK', 'MF', 'FD', 'PPF', 'DERIVATIVES', 'PF'],
                    key="catalog_category"
                )

            with col_b:
                risk_category = st.selectbox(
                    "Risk Category",
                    ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'],
                    key="catalog_risk"
                )

            industry = st.text_input("Industry/Sector", key="catalog_industry")

            submit_catalog = st.form_submit_button("Create Catalog Item")

        if submit_catalog:
            catalog_data = {
                "name": name,
                "symbol": symbol,
                "asset_category": asset_category,
                "risk_category": risk_category,
                "industry": industry
            }
            result = add_catalog_item(catalog_data)

            if result:
                st.success(f"Successfully created '{result['name']}' in the catalog! You can now search for it above.")
                st.cache_data.clear()
                st.rerun()


def render_add_new_asset():
    st.header("Add Investment to Portfolio")

    catalog = fetch_catalog()
    if not catalog:
        st.error("Could not load investment catalog from API. Please ensure the backend is running.")
        return

    catalog_options_map = {
        f"{item['name']} ({item['symbol']}) - [{item['asset_category']}]": item['id']
        for item in catalog
    }
    if not catalog_options_map:
        st.warning("No items found in the Investment Catalog. Please add one below before you can add it to your portfolio.")

    with st.form("new_holding_form"):
        st.subheader("1. Select Investment from Catalog")

        selected_item_display = st.selectbox(
            "Select Investment",
            options=list(catalog_options_map.keys())
        )

        st.subheader("2. Configure Your Holding")
        col1, col2 = st.columns(2)
        with col1:
            nickname = st.text_input("My Nickname (Optional)", placeholder=f"My {selected_item_display.split(' ')[0] if selected_item_display else 'Asset'}")
        with col2:
            sip_frequency = st.selectbox(
                "SIP Frequency",
                options=["NONE", "WEEKLY", "MONTHLY", "YEARLY"]  # Should match SIPFrequency Enum
            )

        submitted_holding = st.form_submit_button("Add to My Portfolio", disabled=(not catalog_options_map))

        if submitted_holding:
            catalog_id = catalog_options_map[selected_item_display]
            holding_data = {
                "catalog_id": catalog_id,
                "nickname": nickname if nickname else None,
                "sip_frequency": sip_frequency
            }
            result = add_user_holding(holding_data)

            if result:
                st.success(f"Successfully added {selected_item_display} to your portfolio!")
                st.cache_data.clear()
                st.rerun()

    st.markdown("---")

    with st.expander("Need to add a new asset to the main Catalog?"):
        with st.form("new_catalog_item_form"):
            st.subheader("Create New Catalog Item")

            c_name = st.text_input("Asset Name (e.g., 'Tata Motors Stock')")
            c_symbol = st.text_input("Symbol (e.g., 'TATAMOTORS')")

            c_col1, c_col2, c_col3 = st.columns(3)
            with c_col1:
                c_asset_cat = st.selectbox(
                    "Asset Category",
                    options=["PF", "PPF", "FD", "MF", "STOCK", "DERIVATIVES"],  # From AssetCategory Enum
                    key="c_asset_cat"
                )
            with c_col2:
                c_risk = st.selectbox(
                    "Risk Category",
                    options=["LOW", "MEDIUM", "HIGH", "VERY_HIGH"],  # From RiskCategory Enum
                    key="c_risk"
                )
            with c_col3:
                c_industry = st.text_input("Industry (e.g., 'Auto', 'Banking')")

            submitted_catalog = st.form_submit_button("Create Catalog Item")

            if submitted_catalog:
                if not c_name or not c_symbol:
                    st.error("Asset Name and Symbol are required.")
                else:
                    catalog_data = {
                        "name": c_name,
                        "symbol": c_symbol,
                        "asset_category": c_asset_cat,
                        "industry": c_industry,
                        "risk_category": c_risk,
                        "status": "ACTIVE"
                    }

                    result = add_catalog_item(catalog_data)

                    if result:
                        st.success(f"Successfully created '{result['name']}' in the catalog! You can now add it to your portfolio above.")
                        st.cache_data.clear()
                        st.rerun()


# def open_scanner_plot(stock_symbol, stock_name , index_data, selected_index):
def open_scanner_plot(stock_symbol, stock_name, selected_index):
    scan_methods = [ 'Mark Minervini', 'WTraders']

    scan_method = st.selectbox('Select scanner', list(scan_methods), index=0)

    if scan_method == 'WTraders':
        pass

    elif scan_method == 'Mark Minervini':
        if api.token is not None or api.login():
            stock_datalist = api.get_stock_data(stock_symbol=stock_symbol, days_ago=MINERVINI_CHART_DAYS_AGO)
            stock_data = pd.DataFrame(stock_datalist)
            if stock_data.empty:
                st.warning(f"No Data returned for {stock_symbol}, probably timed out.")
                return
            stock_data['Date'] = pd.to_datetime(stock_data['Date'], format='%d-%b-%Y')
            stock_data.set_index('Date', inplace=True)

            minvervini =  Minervini()
            minvervini.generate_minnrvini_chart(stock_symbol, stock_name, None, selected_index, stock_data)

            # st.dataframe(stock_data)


def show_live_signals_page_prev():
    st.title("🚀 Minervini Live Signals Dashboard")
    st.markdown("---")

    # 1. FETCH ENRICHED DATA (Joined with Stocks Cache)
    signals = fetch_open_signals()
    if not signals:
        st.warning("No active signals found. Please ensure the scanner is running.")
        return

    df = pd.DataFrame(signals)

    # 2. SMART FILTERS (Sidebar)
    with st.sidebar:
        st.header("⚙️ Portfolio Controls")
        # industries = st.multiselect("Select Industries", options=sorted(df['industry'].unique()), default=df['industry'].unique())
        index_symbols = st.multiselect("Select Index Symbols", options=sorted(df['index_symbol'].unique()), default=df['index_symbol'].unique())
        score_cutoff = st.number_input("Min Financial Score", 0.0, 100.0, 40.0)

    # filtered_df = df[(df['industry'].isin(industries)) & (df['financial_score'] >= score_cutoff)]
    filtered_df = df[(df['index_symbol'].isin(index_symbols)) & (df['financial_score'] >= score_cutoff)]
    # filtered_df = df[(df['financial_score'] >= score_cutoff)]

    # print(filtered_df.head())

    # 3. SUMMARY METRICS
    # m1 = st.columns(1)
    # m1.metric("Current Signals", len(filtered_df))
    # m2.metric("Avg. Profit %", f"{filtered_df['unrealized_pnl_pct'].mean():.2f}%")
    # m3.metric("Highest Alpha", f"{filtered_df['unrealized_pnl_pct'].max():.2f}%")

    # 4. SIGNAL CARDS
    grid = st.columns(6)

    for idx, row in filtered_df.iterrows():
        # Calculate PnL locally if not provided by API
        pnl_pct = ((row['current_market_price'] - row['buy_price']) / row['buy_price']) * 100

        with grid[idx % 6]:
            # Card styling based on PnL
            sentiment = "🟢" if pnl_pct > 0 else "🔴"

            with st.container(border=True):
                # Header: Symbol and Industry
                st.markdown(f"### {sentiment} {row['symbol']}")
                st.caption(f"{row['company_name']} | {row['industry']}")

                # Row 1: Key Performance Metrics
                m1, m2 = st.columns(2)
                m1.metric("PnL %", f"{pnl_pct:.2f}%")
                m2.metric("Fin. Score", int(row['financial_score']))

                # Row 2: Fundamental "Minervini DNA"
                f1, f2 = st.columns(2)
                f1.write(f"**Sales Growth:** {row['sales_growth']}%")
                f2.write(f"**ROCE:** {row['roce']}%")

                st.divider()

                # Row 3: Price & Stop Loss Management
                p1, p2 = st.columns(2)
                p1.write(f"**CMP:** ₹{row['current_market_price']:.2f}")
                p1.write(f"**Entry:** ₹{row['buy_price']:.2f}")

                p2.write(f"**Initial SL:** ₹{row['initial_sl']:.2f}")
                # Highlight Trailing SL as it's the active exit point
                p2.markdown(f":orange[**Trailing SL: ₹{row['current_trailing_sl']:.2f}**]")

                # 5. PYRAMIDING LOGIC (Based on PnL milestones)
                if pnl_pct >= 20:
                    st.success("💎 **Level 2 Pyramid Ready** (+20%)")
                elif pnl_pct >= 10:
                    st.info("📦 **Level 1 Pyramid Ready** (+10%)")

                # 6. ACTION BUTTON
                if st.button(f"Analyze {row['symbol']}", key=f"btn_{row['symbol']}_{row['index_symbol']}", use_container_width=True):
                    st.session_state['active_chart'] = row['symbol']
                    st.session_state['active_name'] = row['company_name']
                    st.session_state['active_index_symbol'] = row['index_symbol']

    # 7. DYNAMIC CHART DISPLAY
    if 'active_chart' in st.session_state:
        selected_symbol = st.session_state['active_chart']
        selected_name = st.session_state['active_name']
        selected_index_symbol = st.session_state['active_index_symbol']

        st.markdown("---")
        st.subheader(f"📈 Real-time Technicals: {selected_symbol} ({selected_name})")

        # Invoking your specific plot function
        # Assuming symbol, selected_name, selected_symbol are passed as per your snippet
        open_scanner_plot(selected_symbol, selected_name, selected_index_symbol)

def show_live_signals_page():
    st.title("🚀 Minervini Live Signals Dashboard")
    st.markdown("---")

    # 1. FETCH ENRICHED DATA
    signals = fetch_open_signals()
    if not signals:
        st.warning("No active signals found. Please ensure the scanner is running.")
        return

    df = pd.DataFrame(signals)

    # ────────────────────────────────────────────────
    #   GROUP BY SYMBOL (keep the "best" or most recent row per symbol)
    # ────────────────────────────────────────────────
    # Strategy: sort by financial_score descending → keep highest score row
    # Alternative options you can swap in:
    #   • .last()   → most recent
    #   • .first()  → first found
    #   • agg(...)  → custom logic
    df_grouped = (
        df.sort_values("financial_score", ascending=False)
          .groupby("symbol", as_index=False)
          .first()
    )

    # ────────────────────────────────────────────────
    #   SIDEBAR FILTERS
    # ────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Portfolio Controls")
        index_symbols = st.multiselect(
            "Select Index Symbols",
            options=sorted(df_grouped["index_symbol"].unique()),
            default=sorted(df_grouped["index_symbol"].unique())
        )
        score_cutoff = st.number_input("Min Financial Score", 0.0, 100.0, 40.0)

    filtered_df = df_grouped[
        (df_grouped["index_symbol"].isin(index_symbols)) &
        (df_grouped["financial_score"] >= score_cutoff)
    ].copy()   # .copy() avoids SettingWithCopyWarning later

    if filtered_df.empty:
        st.info("No signals match the current filters.")
        return

    # ────────────────────────────────────────────────
    #   PAGINATION
    # ────────────────────────────────────────────────
    ITEMS_PER_PAGE = 12

    # Initialize session state for current page
    if "signals_page" not in st.session_state:
        st.session_state.signals_page = 0

    total_items = len(filtered_df)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    # Clamp page number
    st.session_state.signals_page = max(0, min(st.session_state.signals_page, total_pages - 1))

    start_idx = st.session_state.signals_page * ITEMS_PER_PAGE
    end_idx   = start_idx + ITEMS_PER_PAGE

    page_df = filtered_df.iloc[start_idx:end_idx]

    # ────────────────────────────────────────────────
    #   SUMMARY (optional – uncomment if desired)
    # ────────────────────────────────────────────────
    # cols = st.columns(3)
    # cols[0].metric("Current Signals", len(filtered_df))
    # cols[1].metric("Avg. PnL %", f"{filtered_df['unrealized_pnl_pct'].mean():.2f}%")
    # cols[2].metric("Best PnL %", f"{filtered_df['unrealized_pnl_pct'].max():.2f}%")

    st.caption(f"Showing {len(page_df)} of {total_items} signals  •  Page {st.session_state.signals_page + 1} / {total_pages}")

    # ────────────────────────────────────────────────
    #   SIGNAL CARDS – 6 columns × 2 rows = 12 max
    # ────────────────────────────────────────────────
    grid = st.columns(6)

    for idx, row in page_df.iterrows():
        # Calculate PnL locally (fallback)
        pnl_pct = ((row["current_market_price"] - row["buy_price"]) / row["buy_price"]) * 100

        col_idx = idx % 6
        with grid[col_idx]:
            sentiment = "🟢" if pnl_pct > 0 else "🔴"

            with st.container(border=True):
                st.markdown(f"### {sentiment} {row['symbol']}")
                st.write(f"{row['company_name']}")
                # st.divider()
                st.caption(f"{row['industry']}")

                m1, m2 = st.columns(2)
                m1.metric("PnL %", f"{pnl_pct:.2f}%")
                m2.metric("Fin. Score", int(row["financial_score"]))

                f1, f2 = st.columns(2)
                f1.write(f"**Sales Growth:** {row['sales_growth']}%")
                f2.write(f"**ROCE:** {row['roce']}%")

                st.divider()

                p1, p2 = st.columns(2)
                p1.write(f"**CMP:** ₹{row['current_market_price']:.2f}")
                p1.write(f"**Entry:** ₹{row['buy_price']:.2f}")

                p2.write(f"**Initial SL:** ₹{row['initial_sl']:.2f}")
                p2.markdown(f":orange[**Trailing SL: ₹{row['current_trailing_sl']:.2f}**]")

                if pnl_pct >= 20:
                    st.success("💎 **Level 2 Pyramid Ready** (+20%)")
                elif pnl_pct >= 10:
                    st.info("📦 **Level 1 Pyramid Ready** (+10%)")

                if st.button(
                    f"Analyze {row['symbol']}",
                    key=f"btn_{row['symbol']}_{row.get('index_symbol','')}",
                    use_container_width=True
                ):
                    st.session_state["active_chart"] = row["symbol"]
                    st.session_state["active_name"] = row["company_name"]
                    st.session_state["active_index_symbol"] = row.get("index_symbol", "")

    # ────────────────────────────────────────────────
    #   PAGINATION CONTROLS
    # ────────────────────────────────────────────────
    if total_pages > 1:
        st.markdown("---")
        col_prev, col_num, col_next = st.columns([1, 4, 1])

        with col_prev:
            if st.button("← Previous", disabled=st.session_state.signals_page == 0):
                st.session_state.signals_page -= 1
                st.rerun()

        with col_num:
            st.markdown(f"<p style='text-align:center;'>{st.session_state.signals_page + 1} / {total_pages}</p>", unsafe_allow_html=True)

        with col_next:
            if st.button("Next →", disabled=st.session_state.signals_page >= total_pages - 1):
                st.session_state.signals_page += 1
                st.rerun()

    # ────────────────────────────────────────────────
    #   CHART (unchanged)
    # ────────────────────────────────────────────────
    if "active_chart" in st.session_state:
        sym = st.session_state["active_chart"]
        name = st.session_state["active_name"]
        idx_sym = st.session_state.get("active_index_symbol", "")

        st.markdown("---")
        st.subheader(f"📈 Real-time Technicals: {sym} ({name})")
        open_scanner_plot(sym, name, idx_sym)

