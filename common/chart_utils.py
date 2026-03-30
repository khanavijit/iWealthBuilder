import warnings

import pandas as pd
# import yfinance as yf
import plotly.graph_objs as go
import streamlit as st
from plotly.subplots import make_subplots
import numpy as np
import pandas_ta as a_ta


def generate_chart(symbol, stock_name, index_data, selected_index):
    stock_data = yf.download(symbol, period="2y", interval="1wk" ,  multi_level_index=False)
    if stock_data.shape[0] != index_data.shape[0]:
        print(f"Dataframes do not have the same number of rows {stock_name} {symbol}")
        index_data = index_data.tail(len(stock_data)).copy()
        stock_data = stock_data.tail(len(index_data)).copy()
    stock_data['20_HIGH'] = stock_data["High"].rolling(window=20).max()
    stock_data['20_HIGH_10W'] = stock_data['20_HIGH'].rolling(window=5).apply(lambda x: x[-1] == max(x))
    index_data["MA10"] = index_data["Close"].rolling(window=10).mean()
    index_data["barcolor"] = ["red" if c < m else "green" for c, m in zip(index_data["Close"], index_data["MA10"])]
    stock_data['stop_loss'] = np.where(index_data["barcolor"] == "green", stock_data["20_HIGH"] * 0.6, stock_data["20_HIGH"] * 0.9)

    # Add the ROC calculation
    roc_window = 20
    stock_data[f"ROC_{roc_window}"] = (stock_data["Close"] - stock_data["Close"].shift(roc_window)) / stock_data[
        "Close"].shift(roc_window) * 100

    # fig = go.Figure()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['High'], name=stock_name), secondary_y=False)
    fig.add_trace(
        go.Scatter(x=stock_data.index, y=stock_data['20_HIGH'], name='20 Weeks High', line=dict(color='green')),
        secondary_y=False)

    buy_signal = (index_data["barcolor"] == "green") \
                 & (stock_data['High'] >= stock_data['20_HIGH']) \
                 & (stock_data[f"ROC_{roc_window}"] > 20)

    sell_signal = (stock_data['High'].shift(1) > stock_data['stop_loss'].shift(1)) \
                  & (stock_data['High'] < stock_data['stop_loss'])

    for i in range(len(buy_signal)):
        if buy_signal.iloc[i]:
            break
        else:
            sell_signal.iloc[i] = False

    prev_buy = False
    prev_sell = False
    mx_sl = 0
    for i in range(len(buy_signal)):
        mx_sl = max(mx_sl, stock_data.loc[stock_data.index[i], 'stop_loss']) if prev_buy else mx_sl
        if buy_signal.iloc[i]:
            if not prev_buy:
                prev_buy = True
                prev_sell = False
            else:
                buy_signal.iloc[i] = False
        elif sell_signal.iloc[i]:
            if not prev_sell:
                prev_sell = True
                prev_buy = False
            else:
                sell_signal.iloc[i] = False
        if prev_buy and mx_sl > stock_data.loc[stock_data.index[i], 'stop_loss']:
            stock_data.loc[stock_data.index[i], 'stop_loss'] = mx_sl
            pass
        if prev_sell:
            mx_sl = 0
            stock_data.loc[stock_data.index[i], 'stop_loss'] = stock_data.loc[stock_data.index[i], '20_HIGH'] * .9



    fig.add_trace(
        go.Scatter(x=stock_data.index, y=stock_data['stop_loss'], name='Stop Loss', line=dict(color='orange')),
        secondary_y=False)

    fig.add_trace(go.Scatter(x=stock_data.index[buy_signal], y=stock_data['High'][buy_signal], mode="markers",
                             marker=dict(symbol='triangle-down', color="lawngreen", size=12), name="Buy Signal"),
                  secondary_y=False)

    fig.add_trace(go.Scatter(x=stock_data.index[sell_signal], y=stock_data['High'][sell_signal], mode="markers",
                             marker=dict(symbol='triangle-up', color="red", size=12), name="Sell Signal"),
                  secondary_y=False)

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
        title="NIFTY50 Weekly Chart with 10-week MA",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        width=2400,
        height=900
    )

    st.plotly_chart(fig)