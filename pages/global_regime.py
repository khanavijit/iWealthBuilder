"""
Streamlit App for Gold/Nifty Regime Analysis
Interactive dashboard with Plotly charts
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from global_regime_modules.data_fetcher import DataFetcher
from global_regime_modules.regime_analyzer import RegimeAnalyzer


# Page config
st.set_page_config(
    page_title="Gold/Nifty Regime Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #5fa8ff;  
        text-align: center;
        margin-bottom: 0.5rem;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #9aa0a6;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
    }
    
    .metric-card {
        background-color: #141a22;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.8rem 0;
        color: #cfd4da;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.04);
    }
    
    /* REGIME STYLES — DARKER + SHADOWED TEXT */
    
    .regime-RISK_ON {
        background-color: #0b2e1c;
        color: #5fd39b;
        padding: 0.5rem;
        border-radius: 0.3rem;
        border-left: 4px solid #1fa463;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    
    .regime-RISK_OFF {
        background-color: #2a2108;
        color: #d8b75a;
        padding: 0.5rem;
        border-radius: 0.3rem;
        border-left: 4px solid #d6a800;
        text-shadow: 0 1px 1px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.6);
    }
    
    .regime-STRESS {
        background-color: #2e0b0f;
        color: #e06b74;
        padding: 0.5rem;
        border-radius: 0.3rem;
        border-left: 4px solid #c82333;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.85);
    }
    
    .regime-LIQUIDITY_BOOM {
        background-color: #08252b;
        color: #4fb9c6;
        padding: 0.5rem;
        border-radius: 0.3rem;
        border-left: 4px solid #118c9e;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.85);
    }
    </style>

    """, unsafe_allow_html=True)


# Regime colors for Plotly
REGIME_COLORS = {
    'RISK_ON': '#2ecc71',
    'RISK_OFF': '#f39c12',
    'STRESS': '#e74c3c',
    'LIQUIDITY_BOOM': '#3498db'
}

REGIME_COLORS_RGBA = {
    'RISK_ON':       'rgba(46, 204, 113, 0.22)',   # #2ecc71
    'RISK_OFF':      'rgba(243, 156, 18, 0.22)',   # #f39c12
    'STRESS':        'rgba(231, 76, 60, 0.22)',    # #e74c3c
    'LIQUIDITY_BOOM': 'rgba(52, 152, 219, 0.22)',  # #3498db
}


@st.cache_data(ttl=3600)
def load_data(start_date, force_refresh=False):
    """Load and analyze data with caching"""
    fetcher = DataFetcher()
    data = fetcher.fetch_data(start_date=start_date, force_refresh=force_refresh)

    analyzer = RegimeAnalyzer(data)
    analyzer.run_analysis()

    return analyzer


def create_comprehensive_chart(analyzer):
    """Create comprehensive Plotly chart with all panels"""
    df = analyzer.data

    # Create subplots
    fig = make_subplots(
        rows=6, cols=2,
        row_heights=[0.25, 0.15, 0.15, 0.40, 0.25, 0.20],
        column_widths=[0.5, 0.5],
        subplot_titles=(
            'Gold & Nifty Prices with Regime Backgrounds',
            'Gold/Nifty Ratio & 50-day MA',
            '',
            'Nifty RSI',
            'Gold RSI',
            'Cumulative Performance Comparison',
            '',
            'Regime Distribution (Days)',
            'Gold-Nifty Correlation',
        ),
        specs=[
            [{"secondary_y": True, "colspan": 2}, None],
            [{"secondary_y": False, "colspan": 2}, {"type": "scatter"}],
            [{"secondary_y": False}, {"type": "scatter"}],
            [{"secondary_y": False, "colspan": 2}, {"type": "table"}],
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"type": "table"}, {"type": "table"}]
        ],
        vertical_spacing=0.08,
        horizontal_spacing=0.12
    )

    # 1. Prices with regime backgrounds
    # Add regime background shading

    df_copy = df.copy()
    df_copy['regime_change'] = (df_copy['Regime'] != df_copy['Regime'].shift()).cumsum()

    # Build shapes list for regime backgrounds
    shapes = []
    for regime_id, group in df_copy.groupby('regime_change'):
        regime = group['Regime'].iloc[0]
        start_date = group.index[0]
        end_date = group.index[-1] + timedelta(days=1)

        color = REGIME_COLORS.get(regime, 'gray')

        # Convert hex to rgba
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            fillcolor = f"rgba({r},{g},{b},0.3)"
        else:
            fillcolor = color

        shapes.append(dict(
            type="rect",
            xref="x",
            yref="y domain",  # KEY: Use paper coordinates!
            x0=start_date,
            x1=end_date,
            y0=0,
            y1=1,
            fillcolor=fillcolor,
            layer="below",
            line_width=0,
        ))

    # Nifty line
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Nifty'],
            name='Nifty',
            line=dict(color='blue', width=2),
            hovertemplate='Nifty: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=1, secondary_y=False
    )

    # Gold line (secondary y-axis)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Gold'],
            name='Gold',
            line=dict(color='gold', width=2),
            hovertemplate='Gold: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=1, secondary_y=True
    )





    # 2. Gold/Nifty Ratio & 50-day MA
    # 1. Plot the 50-day MA first (reference line – no fill)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Ratio_MA50'],
            name='50-day MA',
            line=dict(color='red', width=2),
            hovertemplate='50-day MA: %{y:.4f}<extra></extra>'
        ),
        row=2, col=1
    )

    # ───────────────────────────────────────────────
    # 2. Plot Ratio line itself (on top, no fill yet)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Ratio'],
            name='Gold/Nifty Ratio',
            line=dict(color='purple', width=1.5),
            hovertemplate='Ratio: %{y:.4f}<extra></extra>'
        ),
        row=2, col=1
    )

    # Prepare masked series (do this only once, before adding traces)
    df['Ratio_above'] = df['Ratio'].where(df['Ratio'] >= df['Ratio_MA50'])
    df['Ratio_below'] = df['Ratio'].where(df['Ratio'] < df['Ratio_MA50'])

    # ───────────────────────────────────────────────
    # 3. Fill when Ratio ≥ 50-day MA  (Gold outperforming → typically "bullish" for ratio)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Ratio_MA50'],  # upper boundary = Ratio
            name='Gold leading (above 50d MA)',
            line=dict(color='rgba(0,0,0,0)'),
            fill='tonexty',  # fills downward → to MA50
            fillcolor='rgba(0, 180, 80, 0.20)',  # semi-transparent green
            showlegend=True,
            hoverinfo='skip'
        ),
        row=2, col=1
    )

    # ───────────────────────────────────────────────
    # 4. Fill when Ratio < 50-day MA  (Nifty outperforming → "bearish" for ratio)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Ratio_MA50'],  # ← upper boundary = MA50
            name='Nifty leading (below 50d MA)',
            line=dict(color='rgba(0,0,0,0)'),
            fill='tonexty',  # fills downward → to Ratio
            fillcolor='rgba(220, 60, 60, 0.18)',  # semi-transparent red
            showlegend=True,
            hoverinfo='skip'
        ),
        row=2, col=1
    )

    # ───────────────────────────────────────────────
    # 5. 200-day MA (added last so it sits on top)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Ratio_MA200'],
            name='200-day MA',
            line=dict(color='blue', width=2.3),  # dashed helps distinguish
            hovertemplate='200-day MA: %{y:.4f}<extra></extra>'
        ),
        row=2, col=1
    )




    # 5. Nifty RSI
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Nifty_RSI'],
            name='Nifty RSI',
            line=dict(color='blue', width=1.5),
            fill='tozeroy',
            hovertemplate='RSI: %{y:.1f}<extra></extra>',
            showlegend=False
        ),
        row=3, col=1
    )

    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    # 6. Gold RSI
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Gold_RSI'],
            name='Gold RSI',
            line=dict(color='gold', width=1.5),
            fill='tozeroy',
            hovertemplate='RSI: %{y:.1f}<extra></extra>',
            showlegend=False
        ),
        row=3, col=2
    )

    fig.add_hline(y=75, line_dash="dash", line_color="red", row=3, col=2)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=2)

    # 7. Cumulative performance
    fig.add_trace(
        go.Scatter(
            x=df.index, y=(df['Nifty_Cumulative'] - 1) * 100,
            name='Buy & Hold Nifty',
            line=dict(color='blue', width=2),
            hovertemplate='Nifty: %{y:.1f}%<extra></extra>'
        ),
        row=4, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index, y=(df['Gold_Cumulative'] - 1) * 100,
            name='Buy & Hold Gold',
            line=dict(color='gold', width=2),
            hovertemplate='Gold: %{y:.1f}%<extra></extra>'
        ),
        row=4, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index, y=(df['Strategy_Cumulative'] - 1) * 100,
            name='Regime Strategy',
            line=dict(color='green', width=3),
            hovertemplate='Strategy: %{y:.1f}%<extra></extra>'
        ),
        row=4, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index, y=(df['Portfolio_60_40_Cumulative'] - 1) * 100,
            name='60/40 Portfolio',
            line=dict(color='purple', width=2, dash='dash'),
            hovertemplate='60/40: %{y:.1f}%<extra></extra>'
        ),
        row=4, col=1
    )

    # 2. Regime distribution
    regime_counts = df['Regime'].value_counts()
    fig.add_trace(
        go.Bar(
            x=regime_counts.index,
            y=regime_counts.values,
            marker_color=[REGIME_COLORS.get(r, 'gray') for r in regime_counts.index],
            text=regime_counts.values,
            textposition='outside',
            hovertemplate='%{x}: %{y} days<extra></extra>',
            showlegend=False
        ),
        row=5, col=1
    )

    # # 4. Correlation
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Correlation'],
            name='Correlation',
            line=dict(color='purple', width=1.5),
            fill='tozeroy',
            hovertemplate='Correlation: %{y:.2f}<extra></extra>',
            showlegend=False
        ),
        row=5, col=2
    )

    fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=2)
    fig.add_hline(y=0.6, line_dash="dash", line_color="red", row=2, col=2,
                  annotation_text="High Corr", annotation_position="right")

    # 8. Performance metrics table
    metrics = analyzer.get_performance_metrics()

    # Convert numpy floats to native Python floats
    def to_py(val):
        return float(val) if isinstance(val, (np.float64, np.float32)) else val

    # Build data with safe conversion
    metrics_data = [
        ['Metric', 'Nifty', 'Gold', 'Strategy', '60/40'],
        ['Total Return %',
         f"{to_py(metrics['total_returns']['nifty']):.1f}",
         f"{to_py(metrics['total_returns']['gold']):.1f}",
         f"{to_py(metrics['total_returns']['regime_strategy']):.1f}",
         f"{to_py(metrics['total_returns']['portfolio_60_40']):.1f}"],
        ['Annual Return %',
         f"{to_py(metrics['annualized_returns']['nifty']):.1f}",
         f"{to_py(metrics['annualized_returns']['gold']):.1f}",
         f"{to_py(metrics['annualized_returns']['regime_strategy']):.1f}",
         f"{to_py(metrics['annualized_returns']['portfolio_60_40']):.1f}"],
        ['Volatility %',
         f"{to_py(metrics['volatility']['nifty']):.1f}",
         f"{to_py(metrics['volatility']['gold']):.1f}",
         f"{to_py(metrics['volatility']['regime_strategy']):.1f}",
         f"{to_py(metrics['volatility']['portfolio_60_40']):.1f}"],
        ['Sharpe Ratio',
         f"{to_py(metrics['sharpe_ratio']['nifty']):.2f}",
         f"{to_py(metrics['sharpe_ratio']['gold']):.2f}",
         f"{to_py(metrics['sharpe_ratio']['regime_strategy']):.2f}",
         f"{to_py(metrics['sharpe_ratio']['portfolio_60_40']):.2f}"]
    ]

    fig.add_trace(
        go.Table(
            header=dict(
                values=metrics_data[0],
                fill_color='lightblue',
                align='center',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=list(zip(*metrics_data[1:])),
                fill_color='white',
                align='center',
                font=dict(size=12, color='black')
            )
        ),
        row=6, col=1
    )

    # 9. Regime stats table
    regime_stats = analyzer.analyze_regime_statistics()

    stats_data = [
        ['Regime', 'Days', '%', 'Avg Nifty %', 'Avg Gold %']
    ]

    for _, row in regime_stats.iterrows():
        stats_data.append([
            row['Regime'],
            f"{row['Days']:.0f}",
            f"{row['Percentage']:.1f}",
            f"{row['Avg_Nifty_Return_%']:.3f}",
            f"{row['Avg_Gold_Return_%']:.3f}"
        ])

    fig.add_trace(
        go.Table(
            header=dict(
                values=stats_data[0],
                fill_color='lightgreen',
                align='center',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=list(zip(*stats_data[1:])),
                fill_color='white',
                align='center',
                font=dict(size=12, color='black')
            )
        ),
        row=6, col=2
    )

    # Update layout
    fig.update_xaxes(title_text="Date", showgrid=False, row=1, col=1)
    fig.update_yaxes(title_text="Nifty", showgrid=False, row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Gold", showgrid=False, row=1, col=1, secondary_y=True)

    fig.update_xaxes(title_text="Regime", row=1, col=2)
    fig.update_yaxes(title_text="Days", row=1, col=2)

    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Ratio", row=2, col=1)

    fig.update_xaxes(title_text="Date", row=2, col=2)
    fig.update_yaxes(title_text="Correlation", row=2, col=2, range=[-1, 1])

    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])

    fig.update_xaxes(title_text="Date", row=3, col=2)
    fig.update_yaxes(title_text="RSI", row=3, col=2, range=[0, 100])

    fig.update_xaxes(title_text="Date", row=4, col=1)
    fig.update_yaxes(title_text="Return %", row=4, col=1)

    # REMOVED: fig.update_yaxes(showticklabels=False, showgrid=False, row=6, col=1)
    # ↑ This line is deleted because row 6 doesn't exist!

    # Apply regime background shapes
    existing_shapes = list(fig.layout.shapes) if fig.layout.shapes else []
    fig.update_layout(shapes=existing_shapes + shapes)

    fig.update_layout(
        height=2000,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )

    return fig


def display_current_status(analyzer):
    """Display current regime status"""
    status = analyzer.get_current_status()

    regime = status['current_regime']
    regime_class = f"regime-{regime.replace(' ', '_')}"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="{regime_class}">
            <h3>Current Regime</h3>
            <h2>{regime}</h2>
            <p>Started: {status['regime_start_date']}</p>
            <p>Days: {status['days_in_regime']}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric(
            "Nifty",
            f"₹{status['current_nifty']:,.0f}",
            f"{status['nifty_change_pct']:+.2f}% (in regime)"
        )
        st.metric("Nifty RSI", f"{status['nifty_rsi']:.1f}" if status['nifty_rsi'] else "N/A")

    with col3:
        st.metric(
            "Gold",
            f"${status['current_gold']:,.0f}",
            f"{status['gold_change_pct']:+.2f}% (in regime)"
        )
        st.metric("Gold RSI", f"{status['gold_rsi']:.1f}" if status['gold_rsi'] else "N/A")

    with col4:
        st.metric("Gold/Nifty Ratio", f"{status['current_ratio']:.4f}")
        st.metric("Correlation", f"{status['correlation']:.2f}" if status['correlation'] else "N/A")

    # Allocation recommendation
    st.markdown("---")
    st.subheader("📊 Recommended Allocation")

    alloc = status['recommended_allocation']

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nifty", f"{alloc['nifty_pct']}%")
    with col2:
        st.metric("Gold", f"{alloc['gold_pct']}%")
    with col3:
        st.metric("Cash", f"{alloc['cash_pct']}%")
    with col4:
        st.info(alloc['description'])

    # Exit signals
    st.markdown("---")
    st.subheader("⚠️ Exit Signals")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Equity Exits:**")
        if status['equity_exit_l3']:
            st.error("🔴 Level 3: FULL EXIT")
        elif status['equity_exit_l2']:
            st.warning("🟠 Level 2: Strong Exit")
        elif status['equity_exit_l1']:
            st.warning("🟡 Level 1: Warning")
        else:
            st.success("✅ No exit signals")

    with col2:
        st.markdown("**Gold Exits:**")
        if status['gold_exit_l3']:
            st.error("🔴 Level 3: FULL EXIT")
        elif status['gold_exit_l2']:
            st.warning("🟠 Level 2: Strong Exit")
        elif status['gold_exit_l1']:
            st.warning("🟡 Level 1: Warning")
        else:
            st.success("✅ No exit signals")


def display_regime_history(analyzer):
    """Display all regime periods with returns"""
    st.subheader("📅 Regime History (All Periods)")

    regime_changes = analyzer.get_regime_changes()
    df_full = analyzer.data

    # Create regime periods
    periods = []

    for i in range(len(regime_changes)):
        start_idx = regime_changes.index[i]

        # Find end date
        if i < len(regime_changes) - 1:
            end_idx = regime_changes.index[i + 1] - timedelta(days=1)
        else:
            end_idx = df_full.index[-1]

        # Get regime data
        regime = regime_changes.iloc[i]['Regime']

        # Calculate returns for this period
        period_data = df_full.loc[start_idx:end_idx]

        if len(period_data) > 0:
            nifty_return = ((period_data['Nifty'].iloc[-1] - period_data['Nifty'].iloc[0]) /
                           period_data['Nifty'].iloc[0] * 100)
            gold_return = ((period_data['Gold'].iloc[-1] - period_data['Gold'].iloc[0]) /
                          period_data['Gold'].iloc[0] * 100)


            periods.append({
                'Start Date': start_idx.strftime('%Y-%m-%d'),
                'End Date': end_idx.strftime('%Y-%m-%d'),
                'Regime': regime,
                'Days': len(period_data),
                'Nifty Return %': round(nifty_return, 2),
                'Gold Return %': round(gold_return, 2)
            })

    # Create DataFrame and display
    df_periods = pd.DataFrame(periods)

    # Style the dataframe
    def color_regime(val):
        colors = {
            'RISK_ON':
                'background-color: #0b2e1c; color: #5fd39b; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);',

            'RISK_OFF':
                'background-color: #2a2108; color: #d8b75a; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);',

            'STRESS':
                'background-color: #2e0b0f; color: #e06b74; text-shadow: 1px 1px 2px rgba(0,0,0,0.85);',

            'LIQUIDITY_BOOM':
                'background-color: #08252b; color: #4fb9c6; text-shadow: 1px 1px 2px rgba(0,0,0,0.85);'
        }
        return colors.get(val, '')

    def color_returns(val):
        if val > 0:
            return 'color: green'
        elif val < 0:
            return 'color: red'
        return ''

    # styled_df = df_periods.style.applymap(
    #     color_regime, subset=['Regime']
    # ).applymap(
    #     color_returns, subset=['Nifty Return %', 'Gold Return %']
    # )

    styled_df = (
        df_periods.style
        .map(color_regime, subset=['Regime'])
        .map(color_returns, subset=['Nifty Return %', 'Gold Return %'])
    )

    st.dataframe(styled_df, width="stretch", height=400)

    # Download button
    csv = df_periods.to_csv(index=False)
    st.download_button(
        label="📥 Download Regime History CSV",
        data=csv,
        file_name=f"regime_history_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


# Main app
def main():
    st.markdown('<div class="main-header">📈 Gold/Nifty Regime Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Market Regime Identification & Trading System</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        start_date = st.date_input(
            "Start Date",
            value=pd.to_datetime('2016-01-01'),
            min_value=pd.to_datetime('2010-01-01'),
            max_value=datetime.now()
        )

        force_refresh = st.checkbox("Force Refresh Data", value=False)

        if st.button("🔄 Reload Analysis", type="primary"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("### 📊 Regime Types")
        st.markdown("""
        - **RISK-ON**: Equities leading
        - **RISK-OFF**: Gold leading
        - **STRESS**: Both falling
        - **LIQUIDITY BOOM**: Both rising
        """)

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        This system analyzes Gold and Nifty markets to identify 
        4 distinct regimes and provides actionable allocation recommendations.
        
        **Data Sources:**
        - Gold: GC=F (Futures)
        - Nifty: ^NSEI
        """)

    # Load data
    with st.spinner('📊 Loading and analyzing data...'):
        try:
            analyzer = load_data(start_date.strftime('%Y-%m-%d'), force_refresh)

            st.success(f"✅ Data loaded: {len(analyzer.data)} trading days from {analyzer.data.index[0].date()} to {analyzer.data.index[-1].date()}")

        except Exception as e:
            st.error(f"❌ Error loading data: {str(e)}")
            return

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "📈 Charts",
        "📅 Regime History",
        "📉 Performance Metrics"
    ])

    with tab1:
        st.header("Current Market Status")
        display_current_status(analyzer)

    with tab2:
        st.header("Comprehensive Analysis")
        with st.spinner('Creating charts...'):
            fig = create_comprehensive_chart(analyzer)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        display_regime_history(analyzer)

    with tab4:
        st.header("Performance Metrics")

        metrics = analyzer.get_performance_metrics()

        st.subheader(f"📊 Analysis Period: {metrics['period_years']} years")

        # Total returns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Nifty Total Return", f"{metrics['total_returns']['nifty']:.1f}%")
        with col2:
            st.metric("Gold Total Return", f"{metrics['total_returns']['gold']:.1f}%")
        with col3:
            st.metric("Strategy Total Return", f"{metrics['total_returns']['regime_strategy']:.1f}%")
        with col4:
            st.metric("60/40 Total Return", f"{metrics['total_returns']['portfolio_60_40']:.1f}%")

        st.markdown("---")

        # Detailed metrics table
        metrics_df = pd.DataFrame({
            'Metric': ['Annualized Return %', 'Volatility %', 'Sharpe Ratio', 'Max Drawdown %'],
            'Nifty': [
                metrics['annualized_returns']['nifty'],
                metrics['volatility']['nifty'],
                metrics['sharpe_ratio']['nifty'],
                metrics['max_drawdown']['nifty']
            ],
            'Gold': [
                metrics['annualized_returns']['gold'],
                metrics['volatility']['gold'],
                metrics['sharpe_ratio']['gold'],
                metrics['max_drawdown']['gold']
            ],
            'Regime Strategy': [
                metrics['annualized_returns']['regime_strategy'],
                metrics['volatility']['regime_strategy'],
                metrics['sharpe_ratio']['regime_strategy'],
                metrics['max_drawdown']['regime_strategy']
            ],
            '60/40 Portfolio': [
                metrics['annualized_returns']['portfolio_60_40'],
                metrics['volatility']['portfolio_60_40'],
                metrics['sharpe_ratio']['portfolio_60_40'],
                metrics['max_drawdown']['portfolio_60_40']
            ]
        })

        st.dataframe(metrics_df, width="stretch")

        st.markdown("---")
        df = analyzer.data.copy()
        df_cumm = df[['Nifty_Cumulative', 'Gold_Cumulative', 'Portfolio_60_40_Cumulative', 'Strategy_Cumulative']]
        st.dataframe(df_cumm, width="stretch")


if __name__ == "__main__":
    main()
