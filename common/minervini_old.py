import numpy as np
import pandas as pd
import pandas_ta as a_ta
import plotly.graph_objs as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

from Constants import INDICATOR_API_USERNAME, INDICATOR_API_HOST, INDICATOR_API_PASSWORD
from common.IndicatorApi import IndicatorApi


class Minervini:
    def __init__(self):  # Corrected the method name
        self.api = IndicatorApi(
            INDICATOR_API_USERNAME,
            INDICATOR_API_PASSWORD,
            host=INDICATOR_API_HOST
        )
        self.api.login()
        self.offline_mode = True

    def generate_minnrvini_chart_2(self, symbol, stock_name, index_data, selected_index, filter_flag = True):
        index_data, length, stock_data = self.clean_data(index_data, selected_index, stock_name, symbol)

        self.generate_technical_indicator(index_data, length, stock_data)

        stock_data['Minervini_flag'] = (
                (stock_data['Close'] > stock_data['50_MA']) &
                (stock_data['50_MA'] > stock_data['150_MA']) &
                (stock_data['14_MA'] > stock_data['50_MA']) &
                (stock_data['Close'] > stock_data['50_MA']) & stock_data['volume_flag']
        )

        stock_data['buy_flag'] = stock_data['volume_flag'] & (stock_data['stop_loss'] < (stock_data['Close'] * .99)) & (index_data["barcolor"] == 'green') & (stock_data['High']>=stock_data['20_HIGH'])
        stock_data['sell_flag'] = (stock_data['stop_loss'] > stock_data['Close'])

        buy_signal = stock_data['buy_flag']
        sell_signal = stock_data['sell_flag']

        buy_signal = buy_signal.fillna(False)
        sell_signal = sell_signal.fillna(False)

        print(stock_data[['buy_flag', 'sell_flag', 'Close', 'stop_loss']].to_string())

        prev_buy, previous_buy_price, total_profit, trades = self.trade_handler(buy_signal, filter_flag, sell_signal, stock_data)

        self.plot_chart(buy_signal, index_data, prev_buy, previous_buy_price, sell_signal, stock_data, stock_name, total_profit, trades)


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
        previous_buy_timestamp = 0
        trades = []
        for i in range(len(buy_signal)):
            mx_sl = max(mx_sl, stock_data.loc[stock_data.index[i], 'stop_loss']) if prev_buy else mx_sl
            if buy_signal.iloc[i]:
                if not prev_buy:
                    previous_buy_price = stock_data.loc[stock_data.index[i], 'Close']
                    previous_buy_timestamp = stock_data.index[i].strftime('%d-%m-%Y')
                    prev_buy = True
                    prev_sell = False
                else:
                    if filter_flag:
                        buy_signal.iloc[i] = False
            if sell_signal.iloc[i]:
                if not prev_sell:
                    sell_date = stock_data.index[i].strftime('%d-%m-%Y')
                    sell_price = stock_data.loc[stock_data.index[i], 'Close']
                    current_profit = (sell_price - previous_buy_price)
                    trades.append({
                        "Buy Date": previous_buy_timestamp,
                        "Buy Price": previous_buy_price,
                        "Sell Date": sell_date,
                        "Sell Price": sell_price,
                        "Profit": current_profit
                    })

                    total_profit = total_profit + current_profit
                    previous_buy_price = 0
                    previous_buy_timestamp = None
                    prev_sell = True
                    prev_buy = False
                else:
                    sell_signal.iloc[i] = False
            if prev_buy and mx_sl > stock_data.loc[stock_data.index[i], 'stop_loss']:
                stock_data.loc[stock_data.index[i], 'stop_loss'] = mx_sl
                pass
            if prev_sell:
                mx_sl = 0
        return prev_buy, previous_buy_price, total_profit, trades

    def generate_technical_indicator(self, index_data, length, stock_data):
        index_data["MA10"] = index_data["Close"].rolling(window=10).mean()
        index_data["barcolor"] = ["red" if c < m else "green" for c, m in zip(index_data["Close"], index_data["MA10"])]
        stock_data['14_MA'] = stock_data['Close'].rolling(window=14).mean()
        stock_data['50_MA'] = stock_data['Close'].rolling(window=50).mean()
        stock_data['150_MA'] = stock_data['Close'].rolling(window=150).mean()
        stock_data['200_MA'] = stock_data['Close'].rolling(window=200).mean()
        stock_data['52_Week_High'] = stock_data['Close'].rolling(window=252).max()
        stock_data['52_Week_Low'] = stock_data['Close'].rolling(window=252).min()
        stock_data['atr'] = a_ta.atr(stock_data['High'], stock_data['Low'], stock_data['Close'], window=length)
        stock_data['atr_mean'] = stock_data['atr'].rolling(window=14).mean()
        stock_data['RSI_14'] = a_ta.rsi(stock_data['Close'], length=14)
        stock_data['RSI_7'] = a_ta.rsi(stock_data['Close'], length=7)
        stock_data['20_HIGH'] = stock_data["High"].rolling(window=20).max()
        stock_data['stop_loss'] = np.where(index_data["barcolor"] == "green", stock_data["20_HIGH"] * 0.6, stock_data["20_HIGH"] * 0.75)
        # stock_data['bull_reversal'] = ((stock_data['RSI_7'].rolling(7).min() <= 35) & (stock_data['RSI_7'] > ((100 - stock_data['RSI_7'].rolling(7).min()) * .2) + stock_data['RSI_7'].rolling(7).min()))
        # stock_data['bear_reversal2'] = ((stock_data['RSI_7'].rolling(7).max() >= 80) & (stock_data['RSI_7'] < (stock_data['RSI_7'].rolling(7).max()) - ((stock_data['RSI_7'].rolling(7).max()) * .28)))
        stock_data['bear_reversal2'] = ((stock_data['RSI_14'].rolling(7).max() >= 70) & (stock_data['RSI_14'] < (stock_data['RSI_14'].rolling(7).max()) - ((stock_data['RSI_14'].rolling(7).max()) * .28)))
        stock_data['bull_reversal'] = (stock_data['RSI_7'] - stock_data['RSI_14']) > 2
        stock_data['bear_reversal'] = (stock_data['RSI_7'] - stock_data['RSI_14']) < -10
        stock_data['volume_14day_sum'] = stock_data['Volume'].shift(2).rolling(window=14).sum()
        stock_data['volume_2day_sum'] = stock_data['Volume'].rolling(window=2).sum()
        # Create a flag to check if the current volume is greater than the past 14 days' sum (excluding today)
        # stock_data['volume_flag'] = stock_data['Volume'] > stock_data['volume_14day_sum']
        stock_data['volume_flag'] = stock_data['volume_2day_sum'] > (stock_data['volume_14day_sum'] * .5)
        stock_data['stop_loss'] = np.where(stock_data["volume_flag"], stock_data["20_HIGH"] * 0.75, stock_data["20_HIGH"] * 0.6)
        stock_data['stop_loss'] = np.where(stock_data['bear_reversal2'], stock_data["20_HIGH"] * 0.70, stock_data['stop_loss'])
        stock_data['stop_loss'] = stock_data["stop_loss"].rolling(window=70).max()
        stock_data['RS_Rating'] = stock_data['Close'].pct_change(126)
        # stock_data['RS_Rating'] = rs_rating[stock_data['Symbol'][0]]  # Assign RS rating
        # Check if 200-day MA is trending up for at least 1 month (21 trading days)
        stock_data['200_MA_Trend'] = stock_data['200_MA'].diff(21) > 0

    def clean_data(self, index_data, selected_index, stock_name, symbol):
        if not index_data:
            index_datalist = self.api.get_stock_data(stock_symbol=selected_index, days_ago=1095, index_flag=True)
            index_data = pd.DataFrame(index_datalist)
            index_data['Date'] = pd.to_datetime(index_data['Date'], format='%d-%b-%Y')
            index_data.set_index('Date', inplace=True)
        stock_symbol = symbol.removesuffix(".NS")
        print(stock_symbol)
        stock_datalist = self.api.get_stock_data(stock_symbol=stock_symbol, days_ago=1095)
        stock_data = pd.DataFrame(stock_datalist)
        stock_data['Date'] = pd.to_datetime(stock_data['Date'], format='%d-%b-%Y')
        stock_data.set_index('Date', inplace=True)
        print(stock_data.head(4).to_string())
        if stock_data.shape[0] != index_data.shape[0]:
            print(f"Dataframes do not have the same number of rows {stock_name}")
            index_data = index_data.tail(len(stock_data)).copy()
            stock_data = stock_data.tail(len(index_data)).copy()
        length = 14
        multiplier = 2.0
        return index_data, length, stock_data

    def plot_chart(self, buy_signal, index_data, prev_buy, previous_buy_price, sell_signal, stock_data, stock_name, total_profit, trades):
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], name=stock_name), secondary_y=False)
        fig.add_trace(
            go.Scatter(x=stock_data.index, y=stock_data['stop_loss'], name='Stop Loss', line=dict(color='orange')),
            secondary_y=False)
        fig.add_trace(go.Scatter(x=stock_data.index[buy_signal], y=stock_data['Close'][buy_signal], mode="markers",
                                 marker=dict(symbol='triangle-up', color="lawngreen", size=12), name="Buy Signal"),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=stock_data.index[sell_signal], y=stock_data['Close'][sell_signal], mode="markers",
                                 marker=dict(symbol='triangle-down', color="red", size=12), name="Sell Signal"),
                      secondary_y=False)
        fig.add_trace(
            go.Bar(x=stock_data.index, y=stock_data['Volume'], name='Volume'), secondary_y=True
        )
        fig.add_trace(
            go.Scatter(
                x=stock_data.index[stock_data['bear_reversal2']],
                y=stock_data['Close'][stock_data['bear_reversal2']],
                mode='markers',
                marker=dict(symbol='star-triangle-down', color='pink', size=15),
                name='Bear Reversal'
            )
        )
        shapes = [
            {
                "type": "rect",
                "x0": index_data.index[i - 1],
                # "y0": index_data["Close"].min(),
                "y0": -stock_data["Close"].max() * 0.1,
                "x1": index_data.index[i],
                # "y1": index_data["Close"].max(),
                "y1": 0,
                # "y1": 2000,
                "fillcolor": index_data["barcolor"][i - 1],
                "opacity": 0.8,
                "line": {"width": 0},
            }
            for i in range(1, len(index_data))
        ]
        fig.update_layout(shapes=shapes)
        fig.update_layout(
            yaxis2=dict(range=[-stock_data['Volume'].max() * 0.1, stock_data['Volume'].max()]),
            title="NIFTY50 Weekly Chart with 10-week MA",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False,
            width=2400,
            height=900
        )
        st.plotly_chart(fig)
        print(f"total profit {total_profit}")
        print(f"total no of trades {len(trades)}")
        print(f"total no of trades {trades}")
        buy_prices = [trade["Buy Price"] for trade in trades]
        if len(buy_prices) > 0:
            average_buy_price = sum(buy_prices) / len(buy_prices)
            normalize_profit = total_profit / average_buy_price * 500
            print(f"normalize_profit {normalize_profit}")
            percentage = round(normalize_profit / 500 * 100, 2)
            print(f"normalize_profit {normalize_profit} ({percentage} %)")
            st.subheader(f"Realized Nomalize profit :  {round(normalize_profit)} ({percentage} %)")
        if prev_buy:
            last_price = stock_data['Close'].iloc[-1]
            total_profit = last_price - previous_buy_price
            normalize_profit = total_profit / previous_buy_price * 500
            percentage = round(normalize_profit / 500 * 100, 2)
            print(f"normalize_profit {normalize_profit} ({percentage} %)")
            st.subheader(f"Unrealized Nomalize profit : {round(normalize_profit)} ({percentage} %)")
        print(stock_data.head(4).to_string())
        print(index_data.head(4).to_string())