import pandas as pd
import yfinance as yf

# --- Step 1: Get the list of NSE Symbols (NIFTY 500 is a common proxy for most traded stocks) ---
# We'll use a URL that reliably provides a list of stocks, in this case, the Nifty 500 list from the NSE.
# Note: The exact URL might change, but the NSE index files are generally stable.
# You could also use a local CSV file if you download the full NSE list (bhavcopy) manually.
try:
    # URL for Nifty 500 constituents (often provided as a CSV download by the exchange)
    # The read_csv function can often read CSV files directly from a URL.
    nifty_500_url = "https://www.nseindia.com/content/indices/ind_nifty500list.csv"
    stock_list_df = pd.read_csv(nifty_500_url)

    print(stock_list_df.to_string())

    # The column with the stock symbols is typically named 'Symbol' or 'Symbol_Name'
    # We select the 'Symbol' column
    symbols = stock_list_df['Symbol'].tolist()

except Exception as e:
    print(f"Error fetching symbols from NSE: {e}")
    print("Using a small default list instead.")
    # Fallback to a small list of known tickers if the URL fails
    symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY']

# --- Step 2: Prepare Tickers for Yahoo Finance ---
# Yahoo Finance requires the '.NS' suffix for NSE stocks.
yahoo_tickers = [symbol + ".NS" for symbol in symbols]

print(f"Attempting to download data for {len(yahoo_tickers)} NSE tickers...")
# print(f"First 5 tickers: {yahoo_tickers[:5]}") # Optional: check the first few tickers

# --- Step 3: Fetch Data using yfinance ---
try:
    # The yf.download function is highly efficient for multiple tickers
    # We fetch data for the last 6 months (e.g., '6mo') at daily interval ('1d')
    all_stocks_data = yf.download(
        tickers=yahoo_tickers,
        period="1mo",  # Fetch data for the last 6 months
        interval="1d",  # Use daily data
        group_by='ticker',  # This organizes the data by stock ticker
        auto_adjust=True,  # Automatically adjusts for splits and dividends
        prepost=False  # Exclude pre and post-market data
    )

    print("\n✅ Data Fetch Successful!")
    print(f"Dataframe structure: {all_stocks_data.shape}")
    print("\nSample Data (First 5 Days of Reliance and TCS):")

    # Access and display data for a couple of stocks for verification
    reliance_data = all_stocks_data['RELIANCE.NS'].head()
    tcs_data = all_stocks_data['TCS.NS'].head()

    print("\nRELIANCE.NS Data:")
    print(reliance_data)

    print("\nTCS.NS Data:")
    print(tcs_data)

    # Optional: Save the data to a CSV file
    # all_stocks_data.to_csv("all_nse_data.csv")
    # print("\nData saved to all_nse_data.csv")

except Exception as e:
    print(f"\n❌ Error during data download: {e}")
    print("Check your internet connection or the list of tickers for validity.")