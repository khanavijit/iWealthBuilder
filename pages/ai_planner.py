import streamlit as st

from common.render_utils import render_ai_allocation_planner

st.title("AI & Allocation Planner")
render_ai_allocation_planner(st.session_state.portfolio_data)