import numpy as np
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from plotly.subplots import make_subplots
import pandas_ta as a_ta

from Constants import INDICATOR_API_USERNAME, INDICATOR_API_HOST, INDICATOR_API_PASSWORD, MINERVINI_CHART_DAYS_AGO, GI_DAYS_AGO
from common.IndicatorApi import IndicatorApi
from common.trade_utils import apply_trailing_sl


class GlobalIndicator:
    def __init__(self):
        self.api = IndicatorApi(
            INDICATOR_API_USERNAME,
            INDICATOR_API_PASSWORD,
            host=INDICATOR_API_HOST
        )
        self.api.login()
        self.offline_mode = True

    def get_global_indicator_data(self):
        df_nifty = self.api.get_global_indicator_data(
            symbol='NIFTY 50', years_ago=GI_DAYS_AGO, apply_indicator=True
        )
        # df_gold = self.api.get_global_indicator_data(
        #     symbol='GOLDBEES', years_ago=GI_DAYS_AGO, apply_indicator=True
        # )
        # df_usdinr = self.api.get_global_indicator_data(
        #     symbol='USDINR', years_ago=GI_DAYS_AGO, apply_indicator=True
        # )
        # df_vix = self.api.get_global_indicator_data(
        #     symbol='INDIA VIX', years_ago=GI_DAYS_AGO, apply_indicator=False
        # )
        return df_nifty

    def plot_chart(self, symbol='NIFTY 50'):
        data = self.get_global_indicator_data()
        df = pd.DataFrame(data)
        print(df.head().to_string())
        df.set_index('date', inplace=True)
        buy_signals = df[df['long_signal']]
        sell_signals = df[df['long_sell']]
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
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name=symbol), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=buy_signals.index,
            y=buy_signals['Close'],
            mode="markers",
            marker=dict(symbol='triangle-up', color="lawngreen", size=12),
            name="Buy Signal"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=sell_signals.index,
            y=sell_signals['Close'],
            mode="markers",
            marker=dict(symbol='triangle-down', color="red", size=12),
            name="Sell Signal"
        ), row=1, col=1)



        # FIX 2: Explicitly set the template and height for better visibility
        fig.update_layout(
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