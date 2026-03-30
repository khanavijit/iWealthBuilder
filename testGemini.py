import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
from typing import Dict, Any, Optional, List
import json
import base64
import time

# --- Configuration & Global Variables ---
# NOTE: The base URL for the backend API is assumed to be running locally on port 8000
API_BASE_URL = "http://127.0.0.1:8000"
st.set_page_config(layout="wide", page_title="iWealthBuilder Dashboard")

# === GEMINI API CONFIGURATION (REQUIRED) ===
# ⚠️ ACTION REQUIRED: Replace "YOUR_API_KEY_HERE" with your actual Gemini API Key.
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-2.5-flash-preview-09-2025"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
# ==========================================


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


# --- API Interaction Functions ---

@st.cache_data(ttl=60)
def fetch_portfolio_summary() -> Optional[Dict[str, Any]]:
    """Fetches combined data (summary + detailed performance) from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/investments/portfolio_summary")
        response.raise_for_status()
        data = response.json()

        # Structure the data to be easily consumable by rendering functions
        performance_list = data.pop('performance_list', [])

        # Rename keys to be more user-friendly for display, if necessary
        for item in performance_list:
            # Ensure the data types are correct for display
            for key in ['total_invested_capital', 'total_withdrawn_capital', 'total_realized_pnl',
                        'current_market_value', 'unrealized_pnl', 'total_units_held']:
                item[key] = float(item.get(key) or 0.0)

        return {
            "portfolio_summary": data,
            "performance_list": performance_list
        }
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        st.error(f"Failed to fetch data from the backend API. Error: {e}")
        return None


def add_transaction(transaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Posts a new transaction to the API."""
    try:
        response = requests.post(f"{API_BASE_URL}/investments/{transaction_data['investment_id']}/transactions", json=transaction_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Failed to add transaction. Check API logs for details. Status: {e.response.status_code}")
        return None


def add_catalog_item(catalog_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Posts a new catalog item to the API."""
    try:
        response = requests.post(f"{API_BASE_URL}/catalog/", json=catalog_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Failed to add catalog item. Status: {e.response.status_code}. Detail: {e.response.json().get('detail')}")
        return None


def add_user_investment(user_inv_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Posts a new user investment (holding) to the API."""
    try:
        response = requests.post(f"{API_BASE_URL}/investments/", json=user_inv_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Failed to add user investment. Status: {e.response.status_code}. Detail: {e.response.json().get('detail')}")
        return None


# --- Gemini API Call Function ---

def get_gemini_suggestion(profile_name: str, portfolio_data: Dict[str, Any]) -> str:
    """Fetches an AI-generated investment suggestion from the Gemini API."""

    if not GEMINI_API_KEY:
        return "⚠️ **ERROR:** Gemini API key is not configured. Please set `GEMINI_API_KEY` in the application file to enable AI features."

    # 1. Prepare data for AI
    summary_data = portfolio_data.get('portfolio_summary', {})
    performance_list = portfolio_data.get('performance_list', [])

    # Format portfolio summary as a simple string for the LLM
    portfolio_summary_text = (
        f"Total Invested: {summary_data.get('total_invested_capital', 0.0):.2f} | "
        f"Total Market Value: {summary_data.get('total_market_value', 0.0):.2f} | "
        f"Net P&L: {summary_data.get('net_profit_loss', 0.0):.2f}\n\n"
        "Individual Asset Performance:\n"
    )
    for asset in performance_list:
        portfolio_summary_text += (
            f"- {asset['investment_name']} (Category: {asset['asset_category']}, SIP: {asset['sip_frequency']}): "
            f"CMV={asset['current_market_value']:.2f}, "
            f"Invested={asset['total_invested_capital']:.2f}, "
            f"Unrealized P&L={asset['unrealized_pnl']:.2f}\n"
        )

    # 2. Define AI persona and prompt
    system_prompt = (
        "You are 'iWealthAI', a sophisticated, friendly, and objective financial advisor. "
        "Your task is to analyze the provided user investment portfolio data, compare it "
        f"against the recommended '{profile_name}' risk profile, and provide actionable, "
        "easy-to-understand investment suggestions in three sections:\n"
        "1. **Analysis Summary:** A brief summary of the user's current allocation health, noting any major category imbalances.\n"
        "2. **Actionable Suggestions:** Specific, concrete actions (e.g., 'Increase SIP for Quant Small Cap Fund by 10%', 'Hold on Reliance Stock', 'Consider booking profit in X').\n"
        "3. **Next Steps:** General advice on market trends relevant to their holdings (e.g., small cap outlook, fixed income strategy) using Google Search grounding.\n"
        "Format the response using bold headers for the sections and clear, conversational language. Do not repeat the input data or allocation percentages in the final output."
    )

    user_query = (
        f"The user wants advice based on their selected risk profile: '{profile_name}'.\n"
        f"The user's current portfolio data is:\n---\n{portfolio_summary_text}\n---\n"
        f"The target allocation profile is for {profile_name}.\n"
        f"Please provide an analysis and suggestions based on this data."
    )

    # 3. Build API Payload
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "tools": [{"google_search": {}}],  # Enable grounding for market trend advice
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    headers = {
        'Content-Type': 'application/json',
    }

    # 4. Make the API Call with Retry Logic (Simple backoff)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()

            result = response.json()
            generated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

            if generated_text:
                return generated_text
            else:
                return f"⚠️ **API Error:** Gemini returned an empty response or an error. Check the response body: {result}"

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                return f"❌ **Request Failed:** Could not get a response from the Gemini API after {max_retries} attempts. Error: {e}"

    return "❌ **API Error:** Unknown communication error."


# --- Rendering Functions ---

def render_dashboard_details(portfolio_data: Dict[str, Any]):
    """Renders the main dashboard summary and charts."""
    summary = portfolio_data['portfolio_summary']
    performance_list = portfolio_data['performance_list']

    st.header("Overall Portfolio Health")

    col1, col2, col3, col4, col5 = st.columns(5)

    # Format and display key metrics
    def format_metric(value):
        return f"₹{value:,.2f}"

    col1.metric("Invested Capital", format_metric(summary['total_invested_capital']))
    col2.metric("Current Market Value", format_metric(summary['total_market_value']))

    net_pnl = summary['net_profit_loss']
    pnl_delta = f"{net_pnl / summary['total_invested_capital'] * 100:.2f}%" if summary['total_invested_capital'] else "0.00%"

    col3.metric("Total Profit/Loss", format_metric(net_pnl), pnl_delta, delta_color="normal" if net_pnl >= 0 else "inverse")
    col4.metric("Realized P&L", format_metric(summary['total_realized_pnl']))
    col5.metric("Unrealized P&L", format_metric(summary['total_unrealized_pnl']))

    st.markdown("---")

    # Create DataFrame for visualizations
    df = pd.DataFrame(performance_list)
    df['unrealized_pnl_percent'] = (df['unrealized_pnl'] / df['total_invested_capital']) * 100

    # 1. Allocation Pie Chart
    st.subheader("Asset Allocation by Value")
    allocation_df = df.groupby('asset_category')['current_market_value'].sum().reset_index()
    fig_pie = px.pie(
        allocation_df,
        values='current_market_value',
        names='asset_category',
        title='Portfolio Distribution by Asset Category',
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 2. Detailed Performance Table
    st.subheader("Individual Investment Performance")

    # Select and reorder columns for display
    display_cols = [
        'investment_name', 'asset_category', 'total_invested_capital',
        'current_market_value', 'unrealized_pnl', 'unrealized_pnl_percent', 'total_units_held'
    ]
    display_df = df[display_cols].copy()

    # Apply number formatting
    for col in ['total_invested_capital', 'current_market_value', 'unrealized_pnl']:
        display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.0f}")

    display_df['unrealized_pnl_percent'] = display_df['unrealized_pnl_percent'].apply(lambda x: f"{x:,.2f}%")

    # Rename columns for presentation
    display_df.columns = [
        'Investment', 'Category', 'Invested Capital', 'Current Value',
        'Unrealized P&L', 'P&L (%)', 'Units Held'
    ]

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_ai_allocation_planner(portfolio_data: Dict[str, Any]):
    """Renders the smart allocation planning and AI suggestion interface."""
    st.header("AI Investment Planner")
    st.markdown("Use this tool to get personalized, AI-driven investment suggestions based on your risk appetite.")

    st.subheader("1. Choose Your Risk Profile")

    # Get current risk profile from session state or set a default
    profile_options = list(ALLOCATION_PROFILES.keys())
    default_index = profile_options.index(st.session_state.get('gemini_profile', 'Moderate (Balanced)'))

    selected_profile = st.selectbox(
        "Select the risk profile you want iWealthAI to analyze your portfolio against:",
        profile_options,
        index=default_index,
        key='gemini_profile'
    )

    st.markdown(f"**Target Allocation for {selected_profile}:**")

    target_allocations = ALLOCATION_PROFILES[selected_profile]
    col_alloc = st.columns(len(target_allocations))

    i = 0
    for category, percent in target_allocations.items():
        with col_alloc[i]:
            st.metric(f"**{category}**", f"{percent}%")
        i += 1

    st.markdown("---")

    # Display Rebalancing Suggestions (Simplified View)
    st.subheader("2. Rebalancing Analysis & AI Suggestion")

    # Add a button to trigger the API call
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


def render_sip_management(portfolio_data: Dict[str, Any]):
    """Renders the interface for managing SIP investments."""
    st.header("SIP Management")
    st.markdown("Manage your Systematic Investment Plans (SIPs) and track their details.")

    df = pd.DataFrame(portfolio_data['performance_list'])

    # Filter for investments with a SIP frequency other than NONE
    sip_df = df[df['sip_frequency'] != 'NONE'].copy()

    if sip_df.empty:
        st.info("You currently have no active investments designated as an SIP.")
        return

    st.subheader("Active SIPs")

    # Display relevant columns for SIPs
    sip_df_display = sip_df[[
        'investment_name',
        'asset_category',
        'sip_frequency',
        'total_invested_capital',
        'current_market_value',
        'unrealized_pnl'
    ]]

    # Apply formatting
    for col in ['total_invested_capital', 'current_market_value', 'unrealized_pnl']:
        sip_df_display[col] = sip_df_display[col].apply(lambda x: f"₹{x:,.0f}")

    sip_df_display.columns = [
        'Investment Name', 'Category', 'Frequency', 'Total Invested', 'Current Value', 'Unrealized P&L'
    ]

    st.dataframe(sip_df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Manage SIP Contribution")
    st.warning("Feature Mock: This section would allow you to model changes to your SIP amounts.")


def render_add_manage_assets():
    """Renders the interface for adding new assets (Catalog) and holdings (User Investment)."""
    st.header("Add/Manage Assets")

    tab_holding, tab_catalog = st.tabs(["Add Investment Holding", "Create New Asset Type (Catalog)"])

    # --------------------------------------------------------
    # TAB 1: Add Investment Holding (UserInvestment)
    # --------------------------------------------------------
    with tab_holding:
        st.subheader("1. Add a New Investment Holding to Your Portfolio")
        st.markdown("This links an asset type from the catalog to your personal portfolio.")

        # Fetch available catalog items for the dropdown
        try:
            catalog_response = requests.get(f"{API_BASE_URL}/catalog/")
            catalog_response.raise_for_status()
            catalog_items = catalog_response.json()
            catalog_map = {f"{item['name']} ({item['symbol']})": item['id'] for item in catalog_items}
            catalog_names = list(catalog_map.keys())
        except requests.exceptions.RequestException:
            st.error("Could not load asset catalog. Ensure the API is running.")
            return

        with st.form("add_holding_form"):
            selected_catalog_name = st.selectbox(
                "Select Asset Type from Catalog",
                catalog_names,
                key="new_holding_catalog"
            )

            # The ID of the selected catalog item
            selected_catalog_id = catalog_map.get(selected_catalog_name)

            nickname = st.text_input(
                "Holding Nickname (e.g., 'My HDFC FD' or 'Zerodha Stock A/C')",
                key="new_holding_nickname"
            )

            sip_frequency = st.selectbox(
                "Default SIP Frequency for this Holding",
                ['NONE', 'MONTHLY', 'YEARLY', 'WEEKLY'],
                key="new_holding_sip"
            )

            submit_holding = st.form_submit_button("Add Investment Holding")

        if submit_holding:
            user_inv_data = {
                "catalog_id": selected_catalog_id,
                "nickname": nickname,
                "sip_frequency": sip_frequency
            }
            result = add_user_investment(user_inv_data)

            if result:
                st.success(f"Successfully added holding '{nickname}'! Now add a transaction for it in the 'Transaction History' or 'SIP Management' tabs.")

                # Clear cache to force a refresh of the portfolio data
                st.cache_data.clear()
                st.rerun()

    # --------------------------------------------------------
    # TAB 2: Create New Asset Type (InvestmentCatalog)
    # --------------------------------------------------------
    with tab_catalog:
        st.subheader("2. Create a New Asset Type in the Catalog")
        st.markdown("Use this only if the asset type (e.g., 'Tesla Stock' or 'New Debt Fund') doesn't exist.")

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
                st.success(f"Successfully created '{result['name']}' in the catalog! You can now add it to your portfolio above.")
                st.cache_data.clear()
                st.rerun()


def render_transaction_history(portfolio_data: Dict[str, Any]):
    """Renders the interface for viewing and adding transactions."""
    st.header("Transaction History")

    # --- 1. Add New Transaction ---
    st.subheader("Add New Transaction")

    performance_list = portfolio_data['performance_list']
    inv_map = {f"{item['investment_name']} ({item['asset_category']})": item['investment_id'] for item in performance_list}
    inv_names = list(inv_map.keys())

    if not inv_names:
        st.warning("Please add an Investment Holding first in the 'Add/Manage Assets' tab.")
        return

    with st.form("add_transaction_form"):
        selected_inv_name = st.selectbox("Select Investment Holding", inv_names, key="tx_investment")
        investment_id = inv_map[selected_inv_name]

        col1, col2 = st.columns(2)
        with col1:
            tx_type = st.selectbox("Transaction Type", ['DEPOSIT', 'WITHDRAWAL'], key="tx_type")
        with col2:
            tx_date = st.date_input("Transaction Date", value=datetime.today().date(), key="tx_date")

        cash_amount = st.number_input("Cash Amount (Required)", min_value=0.01, format="%.2f", key="tx_cash")

        # Unit-based fields (optional)
        st.markdown("---")
        st.markdown("**Optional Fields (Required for Stock/MF/Derivatives):**")
        col3, col4 = st.columns(2)
        with col3:
            units = st.number_input("Units/Quantity", min_value=0.0, format="%.4f", value=0.0, key="tx_units")
        with col4:
            price_per_unit = st.number_input("Price per Unit (if applicable)", min_value=0.0, format="%.4f", value=0.0, key="tx_price")

        submit_tx = st.form_submit_button("Record Transaction", type="primary")

    if submit_tx:
        if cash_amount <= 0:
            st.error("Cash Amount must be greater than zero.")
        else:
            transaction_data = {
                "investment_id": investment_id,
                "type": tx_type,
                "date": datetime.combine(tx_date, datetime.min.time()).isoformat(),
                "cash_amount": cash_amount,
                "units": units if units > 0 else None,
                "price_per_unit": price_per_unit if price_per_unit > 0 else None,
            }

            if add_transaction(transaction_data):
                st.success(f"Successfully recorded {tx_type} transaction!")
                st.cache_data.clear()
                st.rerun()

    # --- 2. View History (Mock) ---
    st.markdown("---")
    st.subheader("Recent Transactions (View-Only Mock)")
    st.info("In a full implementation, this section would fetch detailed transaction history for the selected holding.")

    if performance_list:
        selected_holding = st.selectbox("Select Holding to View History", inv_names)
        # Mock data display
        mock_history = [
            {'Date': '2023-05-20', 'Type': 'WITHDRAWAL', 'Cash': '₹78,000.00', 'Units': 30.0, 'P&L': '₹3,000.00'},
            {'Date': '2022-10-10', 'Type': 'DEPOSIT', 'Cash': '₹250,000.00', 'Units': 100.0, 'P&L': 'N/A'},
        ]
        st.dataframe(pd.DataFrame(mock_history))


# --- Main App Logic ---

def main():
    st.title("iWealthBuilder Investment Tracker")

    # Initialize session state for Gemini suggestion
    if 'gemini_profile' not in st.session_state:
        st.session_state['gemini_profile'] = "Moderate (Balanced)"

    # Fetch data once at the start
    portfolio_data = fetch_portfolio_summary()

    if portfolio_data is None:
        st.error("Failed to connect to the iWealthBuilder API. Please ensure the backend server is running and check console for errors.")
        return

    # Create the tabs
    tab_dashboard, tab_history, tab_planner, tab_sip, tab_add_asset = st.tabs([
        "1. Portfolio Dashboard",
        "2. Transaction History",
        "3. AI & Allocation Planner",
        "4. SIP Management",
        "5. Add/Manage Assets"
    ])

    # Render content inside tabs
    with tab_dashboard:
        render_dashboard_details(portfolio_data)

    with tab_history:
        render_transaction_history(portfolio_data)

    with tab_planner:
        # Pass portfolio_data for the rebalancing part
        render_ai_allocation_planner(portfolio_data)

    with tab_sip:
        render_sip_management(portfolio_data)

    with tab_add_asset:
        render_add_manage_assets()


if __name__ == '__main__':
    main()
