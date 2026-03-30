from common.render_utils import render_dashboard_details
import streamlit as st
st.title("Portfolio Dashboard")
render_dashboard_details(st.session_state.portfolio_data)