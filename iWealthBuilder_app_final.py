from common.api_utils import fetch_portfolio_summary
import streamlit as st
# --- Main App Logic ---

def main():
    st.set_page_config(
        page_title="iWealthBuilder",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ─── Reduce top padding ────────────────────────────────────────────────
    st.markdown("""
        <style>
            /* Main content area */
            .block-container {
                padding-top: 1rem !important;    /* was probably 4–5rem */
                padding-bottom: 1rem !important;
            }

            /* Even tighter if you want almost no space */
            /* .block-container { padding-top: 0.5rem !important; } */

            /* Sidebar top padding */
            section[data-testid="stSidebar"] > div:first-child {
                padding-top: 1rem !important;
            }

            /* Remove header/report padding if needed */
            .stApp > header {
                display: none !important;   /* optional - hides deploy/share buttons */
            }

            /* Make sure title starts higher */
            .st-emotion-cache-1y4p8pa {
                padding-top: 0.5rem !important;
            }
        </style>
    """, unsafe_allow_html=True)
    # st.title("iWealthBuilder Investment Tracker")

    # Initialize session state for Gemini suggestion
    if 'gemini_profile' not in st.session_state:
        st.session_state['gemini_profile'] = "Moderate (Balanced)"

    # Fetch data once at the start
    portfolio_data = fetch_portfolio_summary()


    if portfolio_data is None:
        st.error("Failed to connect to the iWealthBuilder API. Please ensure the backend server is running.")
        return
    if 'portfolio_data' not in st.session_state:
        st.session_state.portfolio_data = portfolio_data

    dashboard_page = st.Page(
        "pages/dashboard.py",
        title="Portfolio Dashboard",
        icon=":material/dashboard:"
    )

    planner_page = st.Page(
        "pages/ai_planner.py",
        title="AI & Allocation Planner",
        icon=":material/smart_toy:"
    )

    sip_page = st.Page(
        "pages/sip.py",
        title="SIP Management",
        icon=":material/payments:"
    )
    assets_page = st.Page(
        "pages/assets.py",
        title="Add/Manage Assets",
        icon=":material/add_circle:"
    )

    catalog_page = st.Page(
        "pages/catalog.py",
        title="Stocks & Index Catalog",
        icon=":material/menu_book:"
    )

    signal_page = st.Page(
        "pages/stock_signals.py",
        title="Live Signals & Portfolio",
        icon=":material/monitoring:"  # Reflects real-time tracking
    )

    global_indicator_page = st.Page(
        "pages/global_indicator.py",
        title="Global Indicator",
        icon=":material/monitoring:"  # Reflects real-time tracking
    )


    config_page = st.Page(
        "pages/config.py",
        title="UI Configuration",
        icon=":material/settings:"
    )

    # 2. Define your NEW page here
    financial_config_page = st.Page(
        "pages/financial_config.py",
        title="Config",
        icon=":material/settings:"
    )

    strategy_planner_page = st.Page(
        "pages/strategy_planner.py",
        title="Strategy & Simulation",
        icon=":material/analytics:"
    )

    help_page = st.Page(
        "pages/Help_Documentation.py",
        title="Help and Documentation",
        icon=":material/developer_guide:"
    )

    global_regime = st.Page(
        "pages/global_regime.py",
        title="Global Regime",
        icon=":material/developer_guide:"
    )

    # 3. Initialize navigation with grouped sections
    pg = st.navigation({
        "Analytics": [dashboard_page, planner_page, strategy_planner_page],  # Added here
        "Operations": [sip_page, assets_page],
        "Global Regime Indicator": [global_regime],
        "Market Data": [catalog_page, signal_page, global_indicator_page, config_page],
        "Prime Rating": [financial_config_page],
        "Information Center": [help_page]
    })


    # Optional: Common sidebar elements (visible on every page)
    st.sidebar.title("Wealth Manager v2.0")
    pg.run()
    # Create the tabs



if __name__ == "__main__":
    main()