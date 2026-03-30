import numpy as np
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from plotly.subplots import make_subplots
import pandas_ta as a_ta

from Constants import INDICATOR_API_USERNAME, INDICATOR_API_HOST, INDICATOR_API_PASSWORD, MINERVINI_CHART_DAYS_AGO
from common.IndicatorApi import IndicatorApi
from common.trade_utils import apply_trailing_sl


class Minervini:
    def __init__(self):
        self.api = IndicatorApi(
            INDICATOR_API_USERNAME,
            INDICATOR_API_PASSWORD,
            host=INDICATOR_API_HOST
        )
        self.api.login()
        self.offline_mode = True

    # ======================================================
    # MAIN ENTRY
    # ======================================================
    def generate_minnrvini_chart(self, symbol, stock_name, index_data, selected_index, stock_data, filter_flag=True, bt=False, generate_signals=False):

        index_data, length, stock_data = self.clean_data(
            index_data, selected_index, stock_name, symbol, stock_data
        )

        self.generate_technical_indicator(index_data, stock_data)

        # ---------------- MINERVINI TREND TEMPLATE ----------------
        stock_data['Minervini_flag'] = (
            (stock_data['Close'] > stock_data['20_MA']) &
            (stock_data['20_MA'] > stock_data['50_MA']) &
            # (stock_data['50_MA'] >= stock_data['150_MA']) &
            # stock_data['200_MA_Trend'] &
            stock_data['near_52W_high']
        )

        # ---------------- BUY LOGIC ----------------
        # Added pocket_ pivot and vcp_flag
        stock_data['buy_flag'] = (
            stock_data['Minervini_flag'] &

            stock_data['near_52W_high'] &
            # (
            #         stock_data['pocket_pivot'] |
            #         stock_data['vcp_flag']
            # ) &
            # (stock_data['Close'] > stock_data['base_high'].shift(1)) &
            stock_data['volume_flag'] &
            (stock_data['RSI_7'] < 80) &

            (index_data["barcolor"] == "green")
        )

        stock_data['stop_loss'] = apply_trailing_sl(stock_data)
        # print(stock_data[['Close', 'stop_loss']].to_string())
        # ---------------- SELL LOGIC ----------------
        stock_data['sell_flag'] = (
               (stock_data['Close'] < stock_data['stop_loss'])
        )

        buy_signal = stock_data['buy_flag'].fillna(False)
        sell_signal = stock_data['sell_flag'].fillna(False)

        if generate_signals:
            latest_bar = stock_data.iloc[-1]
            if latest_bar['buy_flag']:
                print(f"🎯 NEW BUY SIGNAL: {symbol} at {latest_bar['Close']} and stop_loss = {latest_bar['stop_loss']} on date {latest_bar.idx}")
                return True
            else:
                return False

        prev_buy, previous_buy_price, total_profit, trades = self.trade_handler(
            buy_signal, filter_flag, sell_signal, stock_data
        )

        # st.dataframe(stock_data)
        if not bt:
            self.plot_chart(
                buy_signal, sell_signal, stock_data, stock_name, index_data
            )


        FIXED_CAPITAL = 30000  # invest same amount every trade

        print(f"total no of trades {len(trades)}")
        print(f"trades {trades}")

        realized_pnl = 0
        realized_pct_list = []


        if bt:
            FIXED_CAPITAL = 30000
            realized_pnl = 0
            trade_list = []

            # ---------------- PROCESS REALIZED TRADES ----------------
            for trade in trades:
                qty = FIXED_CAPITAL / trade["Buy Price"]
                pnl = (trade["Sell Price"] - trade["Buy Price"]) * qty
                pnl_pct = (pnl / FIXED_CAPITAL) * 100
                realized_pnl += pnl

                trade_list.append({
                    "Symbol": symbol,
                    "Type": "REALIZED",
                    "Buy Date": trade.get("Buy Date"),
                    "Sell Date": trade.get("Sell Date"),
                    "Buy Price": trade.get("Buy Price"),
                    "Sell Price": trade.get("Sell Price"),
                    "PnL": pnl,
                    "PnL %": pnl_pct
                })

            # ---------------- PROCESS UNREALIZED TRADES ----------------
            unrealized_pnl = 0
            unrealized_pct = 0
            if prev_buy:
                last_price = stock_data['Close'].iloc[-1]
                qty = FIXED_CAPITAL / previous_buy_price
                unrealized_pnl = (last_price - previous_buy_price) * qty
                unrealized_pct = (unrealized_pnl / FIXED_CAPITAL) * 100

                trade_list.append({
                    "Symbol": symbol,
                    "Type": "UNREALIZED",
                    "Buy Date": "Held",
                    "Sell Date": "Active",
                    "Buy Price": previous_buy_price,
                    "Sell Price": last_price,
                    "PnL": unrealized_pnl,
                    "PnL %": unrealized_pct
                })

            # --- IF BACKTEST MODE: RETURN DATA ---
            if bt:
                return {
                    "symbol": symbol,
                    "realized_pnl": realized_pnl,
                    "unrealized_pnl": unrealized_pnl,
                    "total_pnl": realized_pnl + unrealized_pnl,
                    "trades": trade_list
                }



        for trade in trades:
            buy_price = trade["Buy Price"]
            sell_price = trade["Sell Price"]

            # Number of shares bought with fixed capital
            qty = FIXED_CAPITAL / buy_price

            # P&L for this trade
            trade_pnl = (sell_price - buy_price) * qty
            trade_pct = (sell_price - buy_price) / buy_price * 100

            realized_pnl += trade_pnl
            realized_pct_list.append(trade_pct)

        # ---------------- REALIZED PERFORMANCE ----------------
        if len(realized_pct_list) > 0:
            avg_trade_pct = round(sum(realized_pct_list) / len(realized_pct_list), 2)
            total_capital = FIXED_CAPITAL * len(realized_pct_list)
            total_pct = round((realized_pnl / total_capital) * 100, 2)

            print(f"Realized P&L ₹{round(realized_pnl, 2)}")
            print(f"Average Trade % {avg_trade_pct}%")
            print(f"Total Capital Used ₹{total_capital}")
            print(f"Realized Return % {total_pct}%")
            if not bt:
                st.subheader(
                    f"Realized Profit: ₹{round(realized_pnl, 2)} "
                    f"({total_pct}%) | Avg Trade: {avg_trade_pct}%"
                )

        # ---------------- UNREALIZED PERFORMANCE ----------------
        if prev_buy:
            last_price = stock_data['Close'].iloc[-1]

            qty = FIXED_CAPITAL / previous_buy_price
            unrealized_pnl = (last_price - previous_buy_price) * qty
            unrealized_pct = round(
                (last_price - previous_buy_price) / previous_buy_price * 100, 2
            )

            print(f"Unrealized P&L ₹{round(unrealized_pnl, 2)}")
            print(f"Unrealized % {unrealized_pct}%")
            if not bt:
                st.subheader(
                    f"Unrealized Profit: ₹{round(unrealized_pnl, 2)} "
                    f"({unrealized_pct}%)"
                )

        if trades:
            realized_df = pd.DataFrame(trades)

            realized_df["Quantity"] = (FIXED_CAPITAL / realized_df["Buy Price"]).astype(int)
            realized_df["Invested Amount"] = realized_df["Quantity"] * realized_df["Buy Price"]
            realized_df["Exit Value"] = realized_df["Quantity"] * realized_df["Sell Price"]
            realized_df["PnL"] = realized_df["Exit Value"] - realized_df["Invested Amount"]
            realized_df["PnL %"] = (realized_df["PnL"] / realized_df["Invested Amount"]) * 100
            if not bt:
                st.subheader("📘 Realized Trades")
                st.dataframe(
                    realized_df.style.format({
                        "Buy Price": "₹{:.2f}",
                        "Sell Price": "₹{:.2f}",
                        "Invested Amount": "₹{:,.0f}",
                        "Exit Value": "₹{:,.0f}",
                        "PnL": "₹{:,.0f}",
                        "PnL %": "{:.2f}%"
                    }),
                    use_container_width=True
                )

                st.markdown(
                    f"**Total Realized PnL:** ₹{realized_df['PnL'].sum():,.0f} "
                    f"({realized_df['PnL'].sum() / realized_df['Invested Amount'].sum() * 100:.2f}%)"
                )
        else:
            if not bt:
                st.info("No realized trades yet.")

    # ======================================================
    # TRADE HANDLER (UNCHANGED)
    # ======================================================
    def trade_handler(self, buy_signal, filter_flag, sell_signal, stock_data):

        for i in range(len(buy_signal)):
            if buy_signal.iloc[i]:
                break
            else:
                sell_signal.iloc[i] = False

        prev_buy = False
        prev_sell = False
        mx_sl = 0
        total_profit = 0
        previous_buy_price = 0
        previous_buy_timestamp = None
        trades = []

        for i in range(len(buy_signal)):
            mx_sl = max(mx_sl, stock_data.iloc[i]['stop_loss']) if prev_buy else mx_sl

            if buy_signal.iloc[i]:
                if not prev_buy:
                    previous_buy_price = stock_data.iloc[i]['Close']
                    previous_buy_timestamp = stock_data.index[i].strftime('%d-%m-%Y')
                    prev_buy = True
                    prev_sell = False
                else:
                    if filter_flag:
                        buy_signal.iloc[i] = False

            if sell_signal.iloc[i] | (stock_data.iloc[i]['Close'] < mx_sl ):
                if not prev_sell:
                    sell_price = stock_data.iloc[i]['Close']
                    sell_date = stock_data.index[i].strftime('%d-%m-%Y')
                    profit = sell_price - previous_buy_price
                    if (not sell_signal.iloc[i]) & (profit < 1.5 * previous_buy_price):
                        continue
                    sell_signal.iloc[i] = True

                    trades.append({
                        "Buy Date": previous_buy_timestamp,
                        "Buy Price": previous_buy_price,
                        "Sell Date": sell_date,
                        "Sell Price": sell_price,
                        "Profit": profit
                    })

                    total_profit += profit
                    previous_buy_price = 0
                    previous_buy_timestamp = None
                    prev_sell = True
                    prev_buy = False
                else:
                    sell_signal.iloc[i] = False

            if prev_buy and mx_sl > stock_data.iloc[i]['stop_loss']:
                stock_data.iloc[i, stock_data.columns.get_loc('stop_loss')] = mx_sl

            if prev_sell:
                mx_sl = 0

        return prev_buy, previous_buy_price, total_profit, trades

    # ======================================================
    # TECHNICAL INDICATORS (PURE MINERVINI)
    # ======================================================
    def generate_technical_indicator(self, index_data, stock_data):

        # -------- Index regime --------
        index_data["MA10"] = index_data["Close"].rolling(10).mean()
        index_data["barcolor"] = np.where(
            index_data["Close"] >= index_data["MA10"], "green", "red"
        )

        # -------- Moving averages --------
        stock_data['50_MA'] = stock_data['Close'].rolling(50).mean()
        stock_data['20_MA'] = stock_data['Close'].rolling(20).mean()
        stock_data['150_MA'] = stock_data['Close'].rolling(150, min_periods=50).mean()
        stock_data['200_MA'] = stock_data['Close'].rolling(200, min_periods=50).mean()

        stock_data['RSI_14'] = a_ta.rsi(stock_data['Close'], length=14)
        stock_data['RSI_7'] = a_ta.rsi(stock_data['Close'], length=7)



        stock_data['bull_reversal'] = ((stock_data['RSI_7'].rolling(7).min() <= 25) & (stock_data['RSI_7'] > ((100 - stock_data['RSI_7'].rolling(7).min()) * .2) + stock_data['RSI_7'].rolling(7).min()))
        stock_data['bear_reversal'] = ((stock_data['RSI_7'].rolling(7).max() >= 85) & (stock_data['RSI_7'] < (stock_data['RSI_7'].rolling(7).max()) - ((stock_data['RSI_7'].rolling(7).max()) * .1)))



        stock_data['200_MA_Trend'] = stock_data['200_MA'].diff(30) > 0

        # -------- 52W high --------
        stock_data['52_Week_High'] = stock_data['Close'].rolling(252, min_periods=50).max()
        stock_data['near_52W_high'] = stock_data['Close'] >= stock_data['52_Week_High'] * 0.85

        # -------- Base breakout --------
        stock_data['base_high'] = stock_data['Close'].rolling(30).max()

        # -------- Volume expansion --------
        stock_data['vol_avg_50'] = stock_data['Volume'].rolling(50).mean()

        vol_spike = stock_data['Volume'] > stock_data['vol_avg_50'] * 5.5

        # True if spike occurred in ANY of last 3 days
        stock_data['volume_flag'] = vol_spike.rolling(3).max().astype(bool)


        # stock_data['volume_flag'] = stock_data['Volume'] > stock_data['vol_avg_50'] * 5.5

        # -------- Relative strength proxy --------
        stock_data['RS_Rating'] = stock_data['Close'].pct_change(126)

        # -------- Fixed Minervini stop --------
        stock_data['stop_loss'] = stock_data['Close'] * 0.92

        additional_indicator = True
        if additional_indicator:

            down_days = stock_data['Close'] < stock_data['Close'].shift(1)

            down_volume_10 = (
                stock_data['Volume']
                .where(down_days)
                .rolling(10)
                .max()
            )

            stock_data['pocket_pivot'] = (
                    (stock_data['Close'] > stock_data['Close'].shift(1)) &
                    (stock_data['Close'] > stock_data['20_MA']) &
                    (stock_data['Volume'] > down_volume_10)
            )

            stock_data['atr'] = a_ta.atr(
                stock_data['High'],
                stock_data['Low'],
                stock_data['Close'],
                length=14
            )

            stock_data['vcp_flag'] = (
                    (stock_data['Volume'] < stock_data['vol_avg_50'] * 0.8) &
                    (stock_data['atr'] < stock_data['atr'].rolling(10).mean()) &
                    (stock_data['Close'] > stock_data['50_MA'])
            )

    # ======================================================
    # DATA CLEANING
    # ======================================================
    def clean_data(self, index_data, selected_index, stock_name, symbol, stock_data):

        if not index_data:
            index_datalist = self.api.get_stock_data(
                stock_symbol=selected_index, days_ago=MINERVINI_CHART_DAYS_AGO, index_flag=True
            )
            index_data = pd.DataFrame(index_datalist)
            index_data['Date'] = pd.to_datetime(index_data['Date'], format='%d-%b-%Y')
            index_data.set_index('Date', inplace=True)

        return index_data, 14, stock_data

    # ======================================================
    # PLOTTING (UNCHANGED)
    # ======================================================
    def plot_chart(self, buy_signal, sell_signal, stock_data, stock_name, index_data):
        stock_data.sort_index(inplace=True)

        # FIX 1: Initialize 2 rows and 1 column.
        # vertical_spacing creates a gap between Price and Volume.
        # row_heights gives 80% space to Price and 20% to Volume.
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.8, 0.2]
        )

        # --- ROW 1: PRICE & SIGNALS ---
        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], name=stock_name), row=1, col=1)

        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['stop_loss'],
                                 name='Stop Loss', line=dict(color='orange')), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=stock_data.index[buy_signal],
            y=stock_data['Close'][buy_signal],
            mode="markers",
            marker=dict(symbol='triangle-up', color="lawngreen", size=12),
            name="Buy Signal"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=stock_data.index[sell_signal],
            y=stock_data['Close'][sell_signal],
            mode="markers",
            marker=dict(symbol='triangle-down', color="red", size=12),
            name="Sell Signal"
        ), row=1, col=1)

        # --- ROW 2: VOLUME ---
        fig.add_trace(
            go.Bar(
                x=stock_data.index,
                y=stock_data['Volume'],
                name='Volume',
                marker=dict(color='lightgrey', line=dict(width=0)),
                opacity=0.5
            ),
            row=2, col=1
        )

        # --- RECTANGLE RIBBON (INDEX BARCOLOR) ---
        shapes = []
        for i in range(1, len(index_data)):
            shapes.append({
                "type": "rect",
                "xref": "x",
                "yref": "paper",
                "x0": index_data.index[i - 1],
                "x1": index_data.index[i],
                "y0": -.19,  # 0 is the very bottom of the chart area
                "y1": -.08,  # 0.03 is slightly above the bottom
                "fillcolor": index_data["barcolor"].iloc[i - 1],
                "opacity": 0.6,
                "line": {"width": 0},
            })

        # FIX 2: Explicitly set the template and height for better visibility
        fig.update_layout(
            shapes=shapes,
            height=600,
            template="plotly_dark",
            showlegend=True,
            xaxis_rangeslider_visible=False,
            margin=dict(t=50, b=50, l=50, r=50),
            legend=dict(
                orientation="h",  # Horizontal legend
                yanchor="bottom",
                y=-0.3,  # Positioned below the chart
                xanchor="center",
                x=0.5
            )
        )

        # Clean up axes
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Vol", showticklabels=False, row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)


