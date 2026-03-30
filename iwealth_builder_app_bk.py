import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
from typing import Dict, Any, Optional, List
import json
import base64

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:8000"
st.set_page_config(layout="wide", page_title="iWealthBuilder Dashboard")

# Global/Constant Allocation Profiles for Smart Allocation Tab
ALLOCATION_PROFILES = {
    "Conservative (Low Risk)": {
        "Equity": 20, "MF": 10, "Bonds": 35, "Fixed": 25, "GOLD/SILVER": 10, "Derivatives": 0
    },
    "Moderate (Balanced)": {
        "Equity": 45, "MF": 15, "Bonds": 20, "Fixed": 10, "GOLD/SILVER": 10, "Derivatives": 0
    },
    "Aggressive (High Risk)": {
        "Equity": 60, "MF": 20, "Bonds": 5, "Fixed": 5, "GOLD/SILVER": 10, "Derivatives": 0
    },
    "High Growth (Very High Risk)": {
        "Equity": 70, "Derivatives": 10, "MF": 15, "Bonds": 0, "Fixed": 0, "GOLD/SILVER": 5
    }
}

# Define known categories and risks for the "Add New Asset" tab
ASSET_CATEGORIES = list(ALLOCATION_PROFILES['Moderate (Balanced)'].keys())
RISK_CATEGORIES = ['Low', 'Medium', 'High', 'Very High']


# --- Helper Functions for API Interaction and Data Mapping ---

@st.cache_data(ttl=5)  # Cache data for 5 seconds to reduce API calls
def get_portfolio_data() -> Optional[Dict[str, Any]]:
    """Fetches the complete portfolio data from the FastAPI backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/data")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Connection Error: Ensure your FastAPI server is running at http://127.0.0.1:8000.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API Error: Failed to fetch portfolio data. Details: {e}")
        return None


def add_transaction(data: dict) -> Optional[Dict[str, Any]]:
    """Posts a new transaction to the FastAPI backend."""
    try:
        # Note the change to use query parameter for investment_name
        inv_name = data.pop('investment_name')
        response = requests.post(f"{API_BASE_URL}/transactions/add?investment_name={inv_name}", json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_detail = response.json().get('detail', 'Unknown error')
        st.error(f"❌ Failed to add transaction (HTTP {response.status_code}): {error_detail}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error communicating with the API: {e}")
        return None


def add_new_investment(data: dict) -> Optional[Dict[str, Any]]:
    """Posts a new investment asset to the FastAPI backend."""
    try:
        response = requests.post(f"{API_BASE_URL}/investments/add", json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_detail = response.json().get('detail', 'Unknown error')
        st.error(f"❌ Failed to add investment (HTTP {response.status_code}): {error_detail}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error communicating with the API: {e}")
        return None


def add_new_sip_definition(data: dict) -> Optional[Dict[str, Any]]:
    """Posts a new SIP definition to the FastAPI backend."""
    try:
        response = requests.post(f"{API_BASE_URL}/sips/add", json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_detail = response.json().get('detail', 'Unknown error')
        st.error(f"❌ Failed to add SIP definition (HTTP {response.status_code}): {error_detail}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error communicating with the API for SIP definition: {e}")
        return None


def update_sip_status_api(sip_id: int, new_status: str) -> Optional[Dict[str, Any]]:
    """Updates the status of an existing SIP."""
    try:
        response = requests.put(f"{API_BASE_URL}/sips/status/{sip_id}?new_status={new_status}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_detail = response.json().get('detail', 'Unknown error')
        st.error(f"❌ Failed to update SIP status (HTTP {response.status_code}): {error_detail}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error communicating with the API: {e}")
        return None


def get_category_to_investments_map(portfolio_data: Dict[str, Any]) -> Dict[str, list]:
    """Returns a map of Category -> List of Investment Names."""
    category_map = {}
    if portfolio_data and 'investments' in portfolio_data:
        for inv_name, details in portfolio_data['investments'].items():
            category = details['category']
            if category not in category_map:
                category_map[category] = []
            category_map[category].append(inv_name)
    return category_map


def get_all_transactions_df(portfolio_data: Dict[str, Any]) -> pd.DataFrame:
    """Combines transactions from all investments into a single DataFrame."""
    all_txns = []
    for inv_name, details in portfolio_data['investments'].items():
        if details.get('transactions'):
            # Convert date_str to date objects if they are strings
            txn_dicts = details['transactions']
            for txn in txn_dicts:
                if isinstance(txn.get('date_str'), str):
                    txn['Date'] = datetime.strptime(txn['date_str'], '%Y-%m-%d').date()
                else:
                    txn['Date'] = txn['date_str']  # Assume it's already a date object
                txn['Investment'] = inv_name
                txn['Category'] = details['category']
                all_txns.append(txn)

    if all_txns:
        master_df = pd.DataFrame(all_txns)
        master_df['Date'] = pd.to_datetime(master_df['Date'])
        master_df = master_df.sort_values(by='Date', ascending=False).reset_index(drop=True)
        return master_df
    return pd.DataFrame()


def render_add_transaction_form(portfolio_data: Dict[str, Any]):
    """Renders the form to add a new transaction (utility function)."""
    if not portfolio_data:
        st.info("Cannot load transaction form: Portfolio data is unavailable.")
        return

    investment_names = list(portfolio_data['investments'].keys())

    with st.form(key='add_txn_form_utility', clear_on_submit=True):
        st.markdown("##### New Transaction Details")

        if not investment_names:
            st.warning("No investments defined in the portfolio yet. Add one in the 'Add New Asset' tab.")
            return

        inv_name = st.selectbox("Investment Name", options=investment_names, key='utility_inv_name')

        col1, col2 = st.columns(2)
        with col1:
            txn_date = st.date_input("Date", value="today", key='utility_txn_date')
            txn_type = st.radio("Type", options=['Buy', 'Sell'], horizontal=True, key='utility_txn_type')

        with col2:
            txn_units = st.number_input("Units", min_value=0.01, format="%.4f", key='utility_txn_units')
            txn_price = st.number_input("Price", min_value=0.01, format="%.2f", key='utility_txn_price')

        submit_button = st.form_submit_button(label='Submit Transaction to API')

        if submit_button:
            txn_data = {
                "investment_name": inv_name,
                "date_str": txn_date.strftime('%Y-%m-%d'),
                "type_str": txn_type,
                "units": txn_units,
                "price": txn_price,
                "utc": 0.0
            }

            result = add_transaction(txn_data)

            if result:
                st.success(result.get('message', "Transaction added successfully!"))
                st.cache_data.clear()
                st.rerun()


# --- Gemini API Call (Placeholder) ---

def get_sentiment_risk_profile(user_prompt: str, profile_keys: list) -> Optional[str]:
    """Placeholder for Gemini API call."""

    # Placeholder Logic for demonstration
    if 'bullish' in user_prompt.lower() or 'booming' in user_prompt.lower():
        suggested_profile = "High Growth (Very High Risk)"
    elif 'worried' in user_prompt.lower() or 'uncertainty' in user_prompt.lower():
        suggested_profile = "Conservative (Low Risk)"
    else:
        suggested_profile = "Moderate (Balanced)"

    st.session_state['gemini_profile'] = suggested_profile
    st.success(f"🤖 Gemini Analysis Placeholder: Risk profile determined as **{suggested_profile}**.")
    return suggested_profile


# --- Tab 1: Portfolio Dashboard & Investment Details ---

def render_dashboard_details(portfolio_data: Dict[str, Any]):
    """Renders the comprehensive dashboard (Tab 1)."""
    summary = portfolio_data.get('summary', {})
    investments = portfolio_data.get('investments', {})

    st.header("✨ Comprehensive Portfolio Dashboard", divider='green')

    # 1. KPI Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Invested Capital", value=f"₹{summary.get('total_invested_capital', 0.0):,.2f}")
    with col2:
        invested = summary.get('total_invested_capital', 0.0)
        market_value = summary.get('total_market_value', 0.0)
        st.metric(label="Total Market Value", value=f"₹{market_value:,.2f}",
                  delta=f"Gain/Loss: ₹{market_value - invested:,.2f}")
    with col3:
        st.metric(label="Overall Absolute Return", value=f"{summary.get('overall_absolute_return_percent', 0.0):,.2f}%")

    st.caption(f"Data calculated as of: {summary.get('last_calculated', 'N/A')}")

    # 2. Asset Allocation Charts
    st.subheader("Asset Allocation Breakdown")

    data_for_chart = []
    for inv_name, details in investments.items():
        data_for_chart.append({
            'Category': details['category'],
            'Market Value': details['metrics']['market_value']
        })
    df_chart = pd.DataFrame(data_for_chart)

    if not df_chart.empty:
        category_df = df_chart.groupby('Category')['Market Value'].sum().reset_index()

        col_pie, col_bar = st.columns(2)

        with col_pie:
            st.markdown("##### Allocation by Category (Market Value)")
            fig = px.pie(
                category_df,
                values='Market Value',
                names='Category',
                hole=.3,
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            # REPLACED: use_container_width=True
            st.plotly_chart(fig, use_container_width=True)

        with col_bar:
            st.markdown("##### Allocation by Risk Category")

            # 1. Create the risk_df (Same logic as before)
            risk_map = {name: inv['risk_category'] for name, inv in investments.items()}

            # Using a list of dictionaries approach is often cleaner than complex assignment/map operations
            risk_data = []
            for inv_name, details in investments.items():
                risk_data.append({
                    'Risk': details['risk_category'],
                    'Market Value': details['metrics']['market_value']
                })

            risk_df = pd.DataFrame(risk_data)

            if not risk_df.empty:
                # Group by Risk and sum Market Value
                risk_df = risk_df.groupby('Risk')['Market Value'].sum().reset_index()

                # Filter to ensure we only have valid risk categories and remove any zero values
                risk_df = risk_df[risk_df['Risk'].isin(RISK_CATEGORIES + ['N/A']) & (risk_df['Market Value'] > 0)]

                # 2. Add validation before charting
                if not risk_df.empty:
                    # Charting using the column names as expected by st.bar_chart if it receives a DataFrame
                    # Using the simpler format for st.bar_chart where it takes a DataFrame

                    # NOTE: Your original code used a PANDAS SERIES: risk_df.set_index('Risk')['Market Value']
                    # We will stick to the Series format but ensure the data is clean.

                    chart_data = risk_df.set_index('Risk')['Market Value']

                    st.bar_chart(chart_data,use_container_width=True)
                else:
                    st.info("Risk data is available but all filtered values are zero.")
            else:
                st.info("No investment data available to calculate risk allocation.")

    # 3. Detailed Holdings Table
    st.subheader("Detailed Investment Holdings")

    flat_data = []
    for inv_name, details in investments.items():
        metrics = details['metrics']

        flat_data.append({
            'Name': details['name'],
            'Category': details['category'],
            'Risk': details['risk_category'],
            'Units': metrics['total_units'],
            'Invested (₹)': metrics['total_invested'],
            'Market Value (₹)': metrics['market_value'],
            'Return (%)': metrics['absolute_return_percent'],
            'CAGR (%)': metrics['cagr']
        })

    df_investments = pd.DataFrame(flat_data)

    if not df_investments.empty:
        st.dataframe(
            df_investments,
            # REPLACED: use_container_width=True
            use_container_width=True,
            column_config={
                'Invested (₹)': st.column_config.NumberColumn(format="₹%,.2f"),
                'Market Value (₹)': st.column_config.NumberColumn(format="₹%,.2f"),
                'Return (%)': st.column_config.ProgressColumn(
                    format="%.2f %%", min_value=-50, max_value=50,
                    help="Absolute Return since inception"
                ),
                'CAGR (%)': st.column_config.NumberColumn(format="%.2f %%"),
            }
        )

    # 4. Add Transaction utility in an expander
    with st.expander("Quick Add New Transaction"):
        render_add_transaction_form(portfolio_data)


# --- Tab 2: Transaction History ---

def render_transaction_history(portfolio_data: Dict[str, Any]):
    """Renders the detailed transaction history (Tab 2)."""
    st.header("📜 Full Transaction History", divider='blue')

    master_df = get_all_transactions_df(portfolio_data)

    if not master_df.empty:
        st.caption(f"Total Transactions: {len(master_df)}")

        # Clean up columns for display
        display_df = master_df[['Date', 'Investment', 'Category', 'type_str', 'units', 'price']].rename(
            columns={'type_str': 'Type', 'units': 'Units', 'price': 'Price'}
        )

        st.dataframe(
            display_df,
            # REPLACED: use_container_width=True
            use_container_width=True,
            column_config={
                'Date': st.column_config.DatetimeColumn(format="YYYY-MM-DD"),
                'Price': st.column_config.NumberColumn(format="₹%,.2f"),
                'Units': st.column_config.NumberColumn(format="%.4f"),
            }
        )

        # Simple analysis: Buy vs Sell over time
        st.subheader("Transaction Volume Over Time")
        # Group by month and transaction type
        tx_volume = master_df.set_index('Date').groupby([pd.Grouper(freq='ME'), 'type_str'])['units'].sum().unstack(fill_value=0)
        # REPLACED: use_container_width=True
        st.line_chart(tx_volume,use_container_width=True)
    else:
        st.info("No transactions recorded yet.")


# --- Tab 3: Smart Allocation & Planning ---

def render_smart_allocation(portfolio_data: Dict[str, Any]):
    """Renders the smart allocation and planning page (Tab 3)."""
    st.header("🧠 Smart Allocation & Future Planning", divider='red')

    # Get map of category to a list of investment names
    category_to_investments_map = get_category_to_investments_map(portfolio_data)

    # 1. Define Investment Goal (Manual or Sentiment-driven)
    st.subheader("1. Define Investment Goal")

    sentiment_prompt = st.text_area(
        "Market Sentiment / Economic Outlook",
        value="The global economy is currently facing moderate inflation and interest rate uncertainty, but I believe long-term tech growth is inevitable.",
        help="Describe your current view to let Gemini suggest an optimal risk profile."
    )

    col_api, col_fund = st.columns([1, 1])

    with col_api:
        analyze_button = st.button("🤖 Analyze & Get Risk Profile",use_container_width=True)  # ADDEDuse_container_width=True

    initial_risk = st.session_state.get('gemini_profile', "Moderate (Balanced)")

    with col_fund:
        fund_amount = st.number_input(
            "New Funds to Allocate (₹)",
            min_value=0.0,
            value=10000.0,
            step=1000.0,
            format="%.2f",
            key='fund_amount_input',
            help="Enter the amount you wish to invest now."
        )

    if analyze_button and sentiment_prompt:
        get_sentiment_risk_profile(sentiment_prompt, list(ALLOCATION_PROFILES.keys()))
        st.rerun()

    selected_risk = st.selectbox(
        "Select Target Risk Profile (Override or Confirm Gemini's Suggestion)",
        options=list(ALLOCATION_PROFILES.keys()),
        index=list(ALLOCATION_PROFILES.keys()).index(initial_risk) if initial_risk in ALLOCATION_PROFILES else 1,
        key='final_risk_profile',
        help="Choose a profile that matches your risk tolerance for new funds."
    )

    st.markdown("---")

    if selected_risk and fund_amount >= 0:
        target_allocation_percentages = ALLOCATION_PROFILES.get(selected_risk, {})

        # --- Calculate New Funds Allocation (DF 1) ---
        if fund_amount > 0:
            allocation_data = []
            for category, percentage in target_allocation_percentages.items():
                amount = fund_amount * (percentage / 100)
                if amount > 0:
                    allocation_data.append({
                        "Asset Category": category,
                        "Target %": percentage,
                        "Suggested Amount (₹)": amount
                    })
            df_new_allocation = pd.DataFrame(allocation_data)

            st.subheader(f"2. Target Allocation for {selected_risk} (New Funds: ₹{fund_amount:,.2f})")

            if not df_new_allocation.empty:

                col_table, col_chart = st.columns([2, 3])
                with col_table:
                    # REPLACED: use_container_width=True
                    st.dataframe(df_new_allocation, hide_index=True,use_container_width=True)
                with col_chart:
                    fig = px.pie(df_new_allocation, values='Suggested Amount (₹)', names='Asset Category', hole=.4)
                    # REPLACED: use_container_width=True
                    st.plotly_chart(fig,use_container_width=True)

                # --- TARGET ALLOCATION ORDER SUBMISSION (Form) ---
                st.markdown("##### Place Order for New Funds: Select Specific Investment per Category")

                with st.form("new_funds_order_form"):
                    order_data = {}

                    form_cols = st.columns(2)

                    for i, (_, row) in enumerate(df_new_allocation.iterrows()):
                        col_index = i % 2
                        with form_cols[col_index]:
                            category = row['Asset Category']
                            amount = row['Suggested Amount (₹)']

                            available_inv = category_to_investments_map.get(category, [])

                            if available_inv:
                                chosen_inv = st.selectbox(
                                    f"Target **{category}** (₹{amount:,.2f})",
                                    options=available_inv,
                                    key=f'target_inv_{category}'
                                )
                                order_data[category] = {'investment': chosen_inv, 'amount': amount}
                            else:
                                st.warning(f"No assets available in category: **{category}**. Add one in the 'Add New Asset' tab.")

                    st.markdown("---")
                    # REPLACED: use_container_width=True
                    submit_target_button = st.form_submit_button("💰 Submit ALL Target Allocation Orders (Buys)", type="primary",use_container_width=True)

                    if submit_target_button:
                        success_count = 0
                        for category, data in order_data.items():
                            inv_name = data.get('investment')
                            amount = data.get('amount')

                            if inv_name and amount and amount > 0:
                                txn_data = {
                                    "investment_name": inv_name,
                                    "date_str": datetime.now().strftime('%Y-%m-%d'),
                                    "type_str": "Buy",
                                    "units": 1.0,
                                    "price": amount,
                                    "utc": 0.0
                                }
                                result = add_transaction(txn_data)
                                if result:
                                    success_count += 1

                        if success_count > 0:
                            st.success(f"✅ Successfully submitted {success_count} 'Buy' orders for new funds! Refreshing dashboard...")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.warning("No orders were submitted or no investments were selected for valid categories.")
                # --- END TARGET ALLOCATION ORDER SUBMISSION ---

            st.markdown("---")

        # --- 3. Rebalancing Actions (Current Holdings + New Funds) ---
        st.subheader("3. Rebalancing Actions (Current Holdings + New Funds)")

        current_data = []
        for inv_name, details in portfolio_data['investments'].items():
            current_data.append({'Category': details['category'], 'Market Value': details['metrics']['market_value']})
        df_current = pd.DataFrame(current_data).groupby('Category')['Market Value'].sum().reset_index()
        df_current.rename(columns={'Market Value': 'Current Market Value (₹)'}, inplace=True)

        df_target_base = pd.DataFrame(list(target_allocation_percentages.items()), columns=['Category', 'Target %'])
        df_target_base['Target %'] = df_target_base['Target %'] / 100.0

        df_rebalance = pd.merge(df_target_base, df_current, on='Category', how='left').fillna(0)

        current_total_market_value = portfolio_data['summary']['total_market_value']
        new_total_portfolio_value = current_total_market_value + fund_amount

        df_rebalance['Target Allocation (₹)'] = df_rebalance['Target %'] * new_total_portfolio_value
        df_rebalance['Action Amount (₹)'] = df_rebalance['Target Allocation (₹)'] - df_rebalance['Current Market Value (₹)']

        def get_action_type(amount):
            if amount > 0:
                return "Buy"
            elif amount < 0:
                return "Sell"
            return "Hold"

        df_rebalance['Action'] = df_rebalance['Action Amount (₹)'].apply(get_action_type)
        df_rebalance['Action Amount (₹)'] = df_rebalance['Action Amount (₹)'].abs()

        df_final = df_rebalance[df_rebalance['Action'] != 'Hold'].sort_values(by='Action Amount (₹)', ascending=False).reset_index(drop=True)

        st.info(f"Goal: Shift total portfolio (₹{new_total_portfolio_value:,.2f}) to match the **{selected_risk}** profile.")

        if not df_final.empty:
            st.dataframe(
                df_final[['Category', 'Current Market Value (₹)', 'Target Allocation (₹)', 'Action', 'Action Amount (₹)']],
                # REPLACED: use_container_width=True
               use_container_width=True,
                column_config={"Current Market Value (₹)": st.column_config.NumberColumn(format="₹%,.2f"), "Target Allocation (₹)": st.column_config.NumberColumn(format="₹%,.2f"), "Action Amount (₹)": st.column_config.NumberColumn(format="₹%,.2f")}
            )
            st.success("The table above shows the exact amounts (current holdings + new funds) required to reach your target risk profile.")

            # --- REBALANCING ORDER SUBMISSION (Form) ---
            st.markdown("##### Execute Rebalancing Trades: Select Specific Investment for Buy/Sell")

            with st.form("rebalance_order_form"):
                rebalance_order_data = {}

                form_cols_rebalance = st.columns(2)

                for i, (_, row) in enumerate(df_final.iterrows()):
                    col_index = i % 2
                    with form_cols_rebalance[col_index]:
                        category = row['Category']
                        action = row['Action']
                        amount = row['Action Amount (₹)']

                        available_inv = category_to_investments_map.get(category, [])

                        if available_inv:
                            chosen_inv = st.selectbox(
                                f"Action **{action}** for **{category}** (₹{amount:,.2f})",
                                options=available_inv,
                                key=f'rebalance_inv_{category}'
                            )
                            rebalance_order_data[category] = {'investment': chosen_inv, 'amount': amount, 'action': action}
                        else:
                            st.error(f"Cannot perform rebalance: No assets available in category: **{category}**.")

                st.markdown("---")
                # REPLACED: use_container_width=True
                submit_rebalance_button = st.form_submit_button("🔄 Submit ALL Rebalancing Orders", type="secondary",use_container_width=True)

                if submit_rebalance_button:
                    success_count = 0
                    for category, data in rebalance_order_data.items():
                        inv_name = data.get('investment')
                        amount = data.get('amount')
                        action = data.get('action')

                        if inv_name and amount and amount > 0:
                            txn_data = {
                                "investment_name": inv_name,
                                "date_str": datetime.now().strftime('%Y-%m-%d'),
                                "type_str": action,
                                "units": 1.0,
                                "price": amount,
                                "utc": 0.0
                            }
                            result = add_transaction(txn_data)
                            if result:
                                success_count += 1

                    if success_count > 0:
                        st.success(f"✅ Successfully submitted {success_count} rebalancing orders! Refreshing dashboard...")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("No orders were submitted or no investments were selected for valid categories.")
            # --- END REBALANCING ORDER SUBMISSION ---

        else:
            st.success("✅ Your current portfolio already perfectly matches the selected target profile for the categories defined!")
    else:
        st.info("Please enter a non-negative amount of funds to allocate.")


# --- Tab 4: SIP Management (Updated) ---

def render_sip_management(portfolio_data: Dict[str, Any]):
    """Renders the SIP management page."""
    st.header("⏳ SIP Management & Tracking", divider='violet')

    sip_definitions = portfolio_data.get('sips', [])

    # 1. Add New SIP Definition Form
    st.subheader("➕ Define New Systematic Investment Plan (SIP)")

    investment_names = list(portfolio_data.get('investments', {}).keys())

    if not investment_names:
        st.warning("No investments defined in the portfolio yet. Add one in the 'Add New Asset' tab before setting up a SIP.")
        return

    with st.form("add_new_sip_form", clear_on_submit=True):

        col1, col2 = st.columns(2)

        with col1:
            sip_inv = st.selectbox("Investment Asset", options=investment_names, key='new_sip_asset')
            sip_amount = st.number_input("Amount (₹)", min_value=100.0, step=100.0, value=5000.0, format="%.2f", key='new_sip_amount_val')

        with col2:
            sip_frequency = st.selectbox(
                "Frequency",
                options=['Monthly', 'Weekly', 'Quarterly', 'One-Time'],
                key='new_sip_frequency'
            )
            start_date = st.date_input("First Investment Date", value=datetime.now().date(), key='new_sip_start_date')

        add_sip_button = st.form_submit_button("Submit New SIP Definition to API", type="primary",use_container_width=True)  # ADDEDuse_container_width=True

        if add_sip_button:
            sip_definition_data = {
                "investment_name": sip_inv,
                "amount": sip_amount,
                "frequency": sip_frequency,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "status": "Active"
            }

            result = add_new_sip_definition(sip_definition_data)

            if result:
                st.success(result.get('message', f"SIP definition added for {sip_inv}!"))
                st.cache_data.clear()
                st.rerun()

    st.markdown("---")

    # 2. Current SIPs Display
    st.subheader("Current SIP Definitions")

    if not sip_definitions:
        st.info("No SIP definitions found in the database yet.")
        return

    sip_df = pd.DataFrame(sip_definitions)

    # Clean up column names and formats for display
    display_cols = ['id', 'investment_name', 'status', 'amount', 'frequency', 'start_date']
    sip_df = sip_df[display_cols].rename(columns={
        'id': 'ID',
        'investment_name': 'Investment',
        'status': 'Status',
        'amount': 'Amount (₹)',
        'frequency': 'Frequency',
        'start_date': 'Start Date'
    })

    st.dataframe(
        sip_df,
        # REPLACED: use_container_width=True
       use_container_width=True,
        hide_index=True,
        column_config={
            'Amount (₹)': st.column_config.NumberColumn(format="₹%,.2f"),
            'Start Date': st.column_config.DateColumn(format="YYYY-MM-DD")
        }
    )

    st.markdown("---")

    # 3. SIP Actions (Update Status)
    st.subheader("SIP Actions: Update Status")

    # Filter for active SIPs to make actions relevant
    active_sips = sip_df[sip_df['Status'] == 'Active']

    if active_sips.empty:
        st.info("No active SIPs to modify or pause.")
        return

    # Use the SIP ID as the identifier
    sip_options = {f"{row['Investment']} (ID: {row['ID']})": row['ID'] for _, row in active_sips.iterrows()}

    with st.form("sip_action_form"):
        col1, col2 = st.columns(2)

        selected_key = col1.selectbox(
            "Select SIP to Modify/Pause",
            options=list(sip_options.keys()),
            key='sip_inv_select'
        )

        selected_id = sip_options[selected_key]
        current_amount = active_sips[active_sips['ID'] == selected_id]['Amount (₹)'].iloc[0]

        action = col2.radio(
            "Action Type",
            options=['Pause SIP', 'Increase Amount (Simulated)', 'Decrease Amount (Simulated)'],
            horizontal=True
        )

        st.markdown("---")

        if action == 'Pause SIP':
            st.warning(f"Confirm pausing the SIP (ID: {selected_id}) for **{selected_key.split('(')[0].strip()}**.")
            submit_label = "Confirm Pause (Update API)"

        elif action in ['Increase Amount (Simulated)', 'Decrease Amount (Simulated)']:
            new_amount = st.number_input(
                f"Enter New SIP Amount (Current: ₹{current_amount:,.2f})",
                min_value=100.0,
                value=float(current_amount * 1.1) if 'Increase' in action else float(current_amount * 0.9),
                step=100.0,
                format="%.2f",
                key='new_sip_amount'
            )
            submit_label = f"Simulate {action}"

        submitted = st.form_submit_button(submit_label, type="secondary",use_container_width=True)  # ADDEDuse_container_width=True

        if submitted:
            if action == 'Pause SIP':
                result = update_sip_status_api(selected_id, "Paused")
                if result:
                    st.success(f"✅ SIP (ID: {selected_id}) is now **PAUSED** via API.")
                    st.cache_data.clear()
                    st.rerun()
            elif 'Simulated' in action:
                st.success(f"✅ SIP for {selected_key.split('(')[0].strip()} is now set to **₹{new_amount:,.2f}** (Simulated).")
                st.info("Note: This is simulated. You need a dedicated API endpoint (PUT) for amount change, and manual transaction recording still applies.")


# --- Tab 5: Add New Asset ---

def render_add_asset_form(portfolio_data: Dict[str, Any]):
    """Renders the form to add a new investment asset (Tab 5)."""
    st.header("➕ Add New Investment Asset", divider='orange')
    st.markdown("Define a new stock, mutual fund, or asset class you plan to invest in before placing an order for it.")

    with st.form(key='add_inv_asset_form', clear_on_submit=True):
        inv_name = st.text_input("Asset Name (e.g., 'Google Stock', 'GoldBees ETF')", key='asset_name')

        col1, col2 = st.columns(2)
        with col1:
            risk = st.selectbox("Risk Category", options=RISK_CATEGORIES, key='asset_risk')
        with col2:
            category = st.selectbox("Asset Category (for Allocation)", options=ASSET_CATEGORIES, key='asset_category')

        submit_button = st.form_submit_button(label='Add New Asset to Portfolio Structure', type="primary",use_container_width=True)  # ADDEDuse_container_width=True

        if submit_button:
            if not inv_name:
                st.error("Asset Name cannot be empty.")
            else:
                asset_data = {
                    "name": inv_name,
                    "category": category,
                    "risk_category": risk,
                    "initial_price": 100.0,
                    "inv_type": "Flexible",
                    "transactions": [],
                    "metrics": {}
                }

                result = add_new_investment(asset_data)

                if result:
                    st.success(result.get('message', f"Asset '{inv_name}' added successfully!"))
                    st.cache_data.clear()


# --- Main App Logic ---

def main():
    st.title("iWealthBuilder Investment Tracker")

    # Initialize session state for Gemini suggestion
    if 'gemini_profile' not in st.session_state:
        st.session_state['gemini_profile'] = "Moderate (Balanced)"

    # Fetch data once at the start
    portfolio_data = get_portfolio_data()

    if portfolio_data is None:
        return

    # Create the five tabs
    tab_dashboard, tab_history, tab_planning, tab_sip, tab_add_asset = st.tabs([
        "1. Portfolio Dashboard",
        "2. Transaction History",
        "3. Smart Allocation & Planning",
        "4. SIP Management",
        "5. Add New Asset"
    ])

    # Render content inside tabs
    with tab_dashboard:
        render_dashboard_details(portfolio_data)

    with tab_history:
        render_transaction_history(portfolio_data)

    with tab_planning:
        render_smart_allocation(portfolio_data)

    with tab_sip:
        render_sip_management(portfolio_data)

    with tab_add_asset:
        render_add_asset_form(portfolio_data)


if __name__ == "__main__":
    main()