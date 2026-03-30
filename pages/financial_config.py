import streamlit as st
from common.api_utils import fetch_scoring_config, save_scoring_config

st.title("⚖️ Financial Scorer Config")
config = fetch_scoring_config()  # Hits your API

if config:
    tab1, tab2 = st.tabs(["Global Cap Defaults", "Sector Specific Rules"])

    with tab1:
        for cap, w in config['default_market_cap'].items():
            with st.expander(f"Standard {cap} Weights", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                w['growth'] = c1.number_input("Growth", value=w['growth'], key=f"g_{cap}")
                w['profitability'] = c2.number_input("Profit", value=w['profitability'], key=f"p_{cap}")
                w['health'] = c3.number_input("Health", value=w['health'], key=f"h_{cap}")
                w['valuation'] = c4.number_input("Valuation", value=w['valuation'], key=f"v_{cap}")

    with tab2:
        # Manage Sector-Level Overrides
        existing_sectors = list(config['sector_overrides'].keys())
        sel_sector = st.selectbox("Select Sector", options=existing_sectors + ["+ Add New Sector"])

        if sel_sector != "+ Add New Sector":
            rules = config['sector_overrides'][sel_sector]
            # Manage specific caps within that sector
            rule_type = st.radio("Apply rule to:", list(rules.keys()) + ["+ Add Specific Cap Override"], horizontal=True)

            if rule_type == "+ Add Specific Cap Override":
                new_c = st.selectbox("Select Cap", ["Large Cap", "Mid Cap", "Small Cap"])
                if st.button("Initialize Override"):
                    config['sector_overrides'][sel_sector][new_c] = rules['default'].copy()
                    save_scoring_config(config)
                    st.rerun()
            else:
                c1, c2, c3, c4 = st.columns(4)
                rules[rule_type]['growth'] = c1.number_input("Growth", value=rules[rule_type]['growth'], key="ov_g")
                # ... repeat for other fields ...

    if st.button("🚀 Push Configuration to Production", type="primary"):
        save_scoring_config(config)
        st.success("Weights updated in CockroachDB!")