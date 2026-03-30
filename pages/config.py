import streamlit as st

from common.api_utils import fetch_index_categories, fetch_indices_by_category, fetch_stocks_by_index, add_api_exclusion, remove_api_exclusion, fetch_api_exclusions

st.title("⚙️ Frontend Configuration")
# init_config_db()

tab1, tab2 = st.tabs(["Add Exclusions", "Manage Blacklist"])

with tab1:
    st.subheader("Exclude Items from UI")
    exclude_type = st.selectbox("What would you like to exclude?", ["Category", "Index", "Stock"])

    if exclude_type == "Category":
        options = fetch_index_categories()
        val = st.selectbox("Select Category to hide", options)
        if st.button("Exclude Category"):
            add_api_exclusion("Category", val)
            st.success(f"Hidden: {val}")

    elif exclude_type == "Index":
        # Using a simple text input or nested selection to get Index name
        cat = st.selectbox("First, pick Category", fetch_index_categories())
        indices = fetch_indices_by_category(cat)
        val = st.selectbox("Select Index to hide", [i['index_name'] for i in indices])
        if st.button("Exclude Index"):
            add_api_exclusion("Index", val)
            st.success(f"Hidden: {val}")

    elif exclude_type == "Stock":
        # Using a simple text input or nested selection to get Index name
        cat = st.selectbox("First, pick Category", fetch_index_categories())
        index = st.selectbox("Pick an index", [i['index_symbol'] for i in fetch_indices_by_category(cat)])
        stocks = fetch_stocks_by_index(index)
        val = st.selectbox("Select Index to hide", [i['symbol'] for i in stocks])
        if st.button("Exclude Stocks"):
            add_api_exclusion("Stock", val)
            st.success(f"Hidden: {val}")

with tab2:
    st.subheader("Currently Excluded Items")
    exclusions = fetch_api_exclusions()
    if exclusions:
        for item in exclusions:
            # Access by keys matches your JSON response
            ex_id = item.get('id')
            ex_type = item.get('exclusion_type')
            ex_val = item.get('exclusion_value')

            col1, col2 = st.columns([3, 1])
            col1.write(f"**{ex_type}**: {ex_val}")

            # Use the ID for the deletion to be precise
            if col2.button("Remove", key=f"del_{ex_id}"):
                remove_api_exclusion(ex_id)  # Better to remove by ID than by value
                st.rerun()
    else:
        st.info("No items are currently excluded.")