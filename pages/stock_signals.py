import streamlit as st

from common.render_utils import show_live_signals_page

if __name__ == "__main__":
    show_live_signals_page()
elif "pg" in globals():
    # This prevents double execution when handled by st.navigation
    show_live_signals_page()