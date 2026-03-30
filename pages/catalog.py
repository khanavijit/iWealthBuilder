import streamlit as st
import pandas as pd

from common.api_utils import fetch_index_categories, fetch_indices_by_category, fetch_stocks_by_index, fetch_prime_score, fetch_ai_score_an_analysis
from common.render_utils import open_scanner_plot

st.set_page_config(page_title="Stocks & Index Catalog", layout="wide")
st.title("📂 Stocks & Index Catalog")
st.write("Browse NSE indices and their constituent stocks from our local database.")

categories = fetch_index_categories()
if categories:
    # --- PRIORITY SORTING ---
    priority_val = "INDICES ELIGIBLE IN DERIVATIVES"
    # Sort: Put priority_val first, then sort the rest alphabetically
    categories = sorted(categories, key=lambda x: (x != priority_val, x))

    selected_cat = st.selectbox("1. Select Category", options=categories)

    if selected_cat:
        # Step 2: Get Indices for that Category
        indices = fetch_indices_by_category(selected_cat)

        if indices:
            # Create a mapping of {Display Name: Symbol}
            idx_map = {item['index_name']: item['index_symbol'] for item in indices}
            selected_name = st.selectbox("2. Select Index", options=list(idx_map.keys()))

            # Step 3: Use the SYMBOL to fetch stocks (Crucial for API accuracy)
            selected_symbol = idx_map[selected_name]
            stocks = fetch_stocks_by_index(selected_name)

            if stocks:
                st.subheader(f"Constituents for {selected_name} ({selected_symbol})")

                # Convert to DataFrame for better display
                df_stocks = pd.DataFrame(stocks)

                # Optional: Reorder columns if they exist to show symbol first
                cols = df_stocks.columns.tolist()
                if 'symbol' in cols:
                    cols.insert(0, cols.pop(cols.index('symbol')))
                    df_stocks = df_stocks[cols]

                # st.dataframe(df_stocks, use_container_width=True, hide_index=True)


                # This turns on row selection
                event = st.dataframe(
                    df_stocks,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",  # Triggers rerun on click
                    selection_mode="single-row",  # Use this exact string
                    key="stock_selector"  # Adding a key is recommended for selection persistence
                )

                # Accessing the selected row
                if event.selection.rows:
                    selected_row_index = event.selection.rows[0]
                    selected_stock = df_stocks.iloc[selected_row_index]
                    symbol = selected_stock['symbol']

                    st.write(f"### Detailed Report for {symbol}")
                    st.divider()
                    open_scanner_plot(symbol, selected_name, selected_symbol)
                    st.divider()
                    with st.expander(f"🔍 Deep Dive: {symbol}", expanded=True):
                        try:
                            res = fetch_prime_score(symbol)

                            st.header(f"{res['company_info']['name']} Analysis")
                            st.info(f"**Verdict:** {res['verdict']} | **Logic:** {res['weightage_logic_used']['basis']}")

                            # --- 2. Key Metric Cards ---
                            m = res['scoring_metrics']
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Overall Score", f"{m['final_score']['total_score_100']}/100")
                            col2.metric("Growth", f"{m['growth_score']}")
                            col3.metric("Profitability", f"{m['profitability_score']}")
                            col4.metric("Valuation", f"{m['valuation_score']}")

                            # --- 3. Sentiment & Chart Section ---
                            # Creating a split layout for Sentiment and the small Bar Chart
                            left_col, right_col = st.columns([1, 1])

                            with left_col:
                                st.subheader("Quarterly Trend")
                                # Convert historical data to DataFrame
                                df_hist = pd.DataFrame(res['historical_quarterly_scores'])
                                df_hist['date_obj'] = pd.to_datetime(df_hist['period'], format='%b %Y')

                                # 3. Sort by the actual date objects
                                df_hist = df_hist.sort_values(by='date_obj')

                                # 4. CRITICAL STEP: Set 'period' as a Categorical type
                                # This tells Streamlit: "Do not alphabetize these strings; follow this exact order."
                                df_hist['period'] = pd.Categorical(df_hist['period'], categories=df_hist['period'], ordered=True)

                                # 5. Plot the bar chart
                                # We select only the 'score' column to avoid plotting the 'date_obj'
                                st.bar_chart(df_hist.set_index('period')[['score']], height=200)
                                # Replace line_chart with bar_chart
                                # We set the index to 'period' so the labels appear on the X-axis
                                # st.bar_chart(df_hist.set_index('period'), height=250)

                            with right_col:
                                st.subheader(f"Market Sentiment {symbol}")
                                # 1. Create a placeholder container
                                sentiment_placeholder = st.empty()

                                with st.spinner("Analyzing..."):
                                    # Fetch the new data
                                    new_data = fetch_ai_score_an_analysis(symbol)
                                    st.info(symbol)
                                    with sentiment_placeholder.container():
                                        st.success(f"**AI Score: {new_data['score']}/20**")
                                        st.info(new_data['narrative'])

                                    st.toast("Analysis synchronized with database!")



                            # --- 4. Logic Details ---
                            with st.expander("View Weightage Distribution"):
                                st.json(res['weightage_logic_used']['weights'])



                        except Exception as e:
                            st.warning(f"Analysis report not yet generated for this stock. {e}")
            else:
                st.info(f"No constituents found for {selected_symbol}.")
        else:
            st.warning(f"No indices found under the category: {selected_cat}")
else:
    st.error("Could not fetch categories. Please check if the FastAPI server is running.")