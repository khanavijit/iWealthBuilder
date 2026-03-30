import json
import time
import argparse

import numpy as np
import pandas as pd

from Constants import INDICATOR_API_USERNAME, INDICATOR_API_HOST, INDICATOR_API_PASSWORD, MINERVINI_CHART_DAYS_AGO
from common.IndicatorApi import IndicatorApi
from common.api_utils import fetch_get_stock_full_analysis, post_new_signal
from common.minervini import Minervini


def run_minervini_bulk_bt_prev(api_response, minervini_engine, api_service):
    """
    api_response: The JSON data you just fetched for NIFTY 100
    minervini_engine: Your Minervini class instance
    api_service: Your API object to fetch historical OHLCV
    """
    all_trade_reports = []
    index_name = api_response.get('index', 'Unknown')
    stock_list = api_response.get('data', [])

    print(f"🚀 Starting Minervini Bulk Backtest for {len(stock_list)} stocks...")

    ROCE_THRESHOLD = 20.0
    FIN_SCORE_THRESHOLD = 60.0

    for item in stock_list:
        symbol = item['symbol']
        fundamentals = item['fundamentals']
        # print(f"🚀 Currently Minervini Backtest for {symbol} ... {fundamentals}")

        # 1. EXTRACT SCORES
        f_score = fundamentals.get('financial_score', 0)
        roce = fundamentals.get('roce', 0)

        # 2. APPLY FILTER (Only proceed if stock meets criteria)
        if f_score > FIN_SCORE_THRESHOLD and roce > ROCE_THRESHOLD:
            print(f"✅ Pattern Match: {symbol} (Fin: {f_score}, ROCE: {roce})")
        else:
            # Skip this stock and move to the next one
            continue

        try:
            # 1. Fetch Historical OHLCV Data for the technical scan
            # Replace with your actual history fetching method
            stock_datalist = api_service.get_stock_data(stock_symbol=symbol, days_ago=MINERVINI_CHART_DAYS_AGO)
            stock_data = pd.DataFrame(stock_datalist)

            if stock_data.empty:
                continue

            stock_data['Date'] = pd.to_datetime(stock_data['Date'])
            stock_data.set_index('Date', inplace=True)

            # 2. Run Backtest (bt=True returns dict instead of plotting)
            # This uses the 16% Initial / 70% Trailing SL logic
            bt_result = minervini_engine.generate_minnrvini_chart(
                symbol, symbol, None, index_name, stock_data, bt=True
            )

            if bt_result and bt_result['trades']:
                for trade in bt_result['trades']:
                    # Merge fundamental data into the trade report for significance analysis
                    report_entry = {
                        "Symbol": symbol,
                        **fundamentals,  # Unpacks financial_score, profit_growth, etc.
                        **trade  # Unpacks Buy Price, Sell Price, PnL, PnL %
                    }
                    all_trade_reports.append(report_entry)

        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")

    # 3. Create Detailed CSV Report
    report_df = pd.DataFrame(all_trade_reports)
    report_df.to_csv(f"../reports/Minervini_Detailed_Report_{index_name}.csv", index=False)

    print(f"✅ Job Complete. Report saved to Minervini_Detailed_Report_{index_name}.csv")
    return report_df


def run_minervini_bulk_bt(api_response, minervini_engine, api_service, generate_signals=False):
    all_trade_reports = []
    index_name = api_response.get('index', 'Unknown')
    stock_list = api_response.get('data', [])

    processed_symbols = set()
    FIXED_CAPITAL_PER_STOCK = 30000
    FIN_SCORE_LIMIT = 40  # Floor for Quality
    ROCE_LIMIT = 30.0  # Floor for Efficiency (The 'Secret' to 90% WinRate)
    SALES_GROWTH_LIMIT = 20.0  # Floor for Momentum Engine

    print(f"🚀 Starting Filtered Backtest for {index_name}...")

    for item in stock_list:
        symbol = item['symbol']
        fundamentals = item['fundamentals']

        # --- 1. FUNDAMENTAL FILTER ---
        f_score = fundamentals.get('financial_score', 0)
        roce = fundamentals.get('roce', 0)
        sales = fundamentals.get('sales_growth', 0)

        if symbol in processed_symbols:
            continue
        processed_symbols.add(symbol)

        if f_score < FIN_SCORE_LIMIT or roce < ROCE_LIMIT or sales < SALES_GROWTH_LIMIT:
            continue  # Skip laggards

        try:
            # Fetch Historical Data
            stock_datalist = api_service.get_stock_data(stock_symbol=symbol, days_ago=MINERVINI_CHART_DAYS_AGO)
            stock_data = pd.DataFrame(stock_datalist)

            if stock_data.empty:
                continue

            stock_data['Date'] = pd.to_datetime(stock_data['Date'])
            stock_data.set_index('Date', inplace=True)

            # --- 2. EXECUTE STRATEGY ---
            bt_result = minervini_engine.generate_minnrvini_chart(
                symbol, symbol, None, index_name, stock_data, bt=True, generate_signals=generate_signals
            )
            if generate_signals:
                if bt_result is True:
                    latest_bar = stock_data.iloc[-1]
                    payload = {
                        "symbol": symbol,
                        "buy_date": str(latest_bar.name.date()),
                        "buy_price": float(latest_bar['Close']),
                        "stop_loss": float(latest_bar['stop_loss']),
                        "financial_score": float(fundamentals.get('financial_score', 0))
                    }
                    # Push to FastAPI
                    post_new_signal(payload)
                continue

            # --- 3. SAFE TRADE PROCESSING ---
            # Ensure bt_result is a dictionary and 'trades' is a valid list
            if isinstance(bt_result, dict) and isinstance(bt_result.get('trades'), list):
                trades = bt_result['trades']

                if not trades:
                    print(f"ℹ️ {symbol}: No technical signals found.")
                    continue

                for trade in trades:
                    # Use .get() to avoid KeyError if 'Buy Price' or 'Sell Price' is missing
                    buy_price = trade.get('Buy Price')
                    sell_price = trade.get('Sell Price')

                    # Only calculate if both prices exist and are numeric
                    if buy_price and sell_price:
                        qty = FIXED_CAPITAL_PER_STOCK / buy_price
                        actual_pnl = (sell_price - buy_price) * qty

                        report_entry = {
                            "Symbol": symbol,
                            **fundamentals,
                            **trade,
                            "Actual_PnL": actual_pnl
                        }
                        all_trade_reports.append(report_entry)
                    else:
                        print(f"⚠️ {symbol}: Incomplete trade data (Missing prices).")

        except Exception as e:
            # This catches things like 'NoneType' errors if bt_result is None
            print(f"❌ Error processing {symbol}: {str(e)}")

    # --- 4. CALCULATE METRICS ---
    if not all_trade_reports:
        print("❌ No trades were generated for the current filters.")
        return pd.DataFrame()

    df = pd.DataFrame(all_trade_reports)

    # Convert columns to numeric to avoid calculation errors
    df['Actual_PnL'] = pd.to_numeric(df['Actual_PnL'], errors='coerce')
    df['PnL %'] = pd.to_numeric(df['PnL %'], errors='coerce')

    # Aggregation Logic
    total_trades = len(df)
    winning_trades = df[df['PnL %'] > 0]
    losing_trades = df[df['PnL %'] <= 0]

    win_rate = (len(winning_trades) / total_trades) * 100
    total_profit = df['Actual_PnL'].sum()
    avg_pnl_pct = df['PnL %'].mean()

    # Performance Analysis
    gross_profit = winning_trades['Actual_PnL'].sum()
    gross_loss = abs(losing_trades['Actual_PnL'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')

    # --- 5. DISPLAY PERFORMANCE REPORT ---
    print("\n" + "=" * 40)
    print(f"📊 BACKTEST REPORT: {index_name}")
    print("=" * 40)
    print(f"Total Trades:         {total_trades}")
    print(f"Win Rate:             {win_rate:.2f}%")
    print(f"Total Realized PnL:   ₹{total_profit:,.2f}")
    print(f"Avg Profit per Trade: {avg_pnl_pct:.2f}%")
    print(f"Profit Factor:        {profit_factor:.2f}")
    print(f"Best Trade:           {df['PnL %'].max():.2f}%")
    print(f"Worst Trade:          {df['PnL %'].min():.2f}%")
    print("=" * 40)

    df.to_csv(f"../reports/Minervini_Analysis_{index_name}.csv", index=False)
    return df
if __name__ == "__main__":

    # payload = {
    #     "symbol": 'ANANDRATHI',
    #     "buy_date": str('22-01-2026'),
    #     "buy_price": float('3092'),
    #     "stop_loss": float('2988'),
    #     "financial_score": float(61.2)
    # }
    # # Push to FastAPI
    # post_new_signal(payload)



    index_symbol ='NIFTY 500'
    new_data = fetch_get_stock_full_analysis(index_symbol)
    minervini = Minervini()
    api = IndicatorApi(INDICATOR_API_USERNAME, INDICATOR_API_PASSWORD, host=INDICATOR_API_HOST)
    generate_signals = False
    if api.token is not None or api.login():
    # 3. Run the Job
        final_report = run_minervini_bulk_bt(new_data, minervini, api, generate_signals=generate_signals)
        if not generate_signals and not final_report.empty:
            # 1. Filter for only numeric columns (this removes 'Symbol', 'Date', etc.)
            numeric_df = final_report.select_dtypes(include=[np.number])

            # 2. Run correlation on the numeric data only
            if 'PnL %' in numeric_df.columns:
                corrs = numeric_df.corr()['PnL %'].sort_values(ascending=False)
                print("\n--- Significance Analysis (Correlation with Profit) ---")
                print(corrs)
            else:
                print("PnL % column not found in numeric data.")