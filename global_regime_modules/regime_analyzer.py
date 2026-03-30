"""
Core Regime Analyzer Module
Contains all the logic for regime identification and analysis
NO data fetching - only analysis logic
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class RegimeAnalyzer:
    """
    Analyzes market regimes based on Gold and Nifty performance
    Identifies 4 regimes: RISK-ON, RISK-OFF, STRESS, LIQUIDITY BOOM
    """
    
    def __init__(self, data):
        """
        Initialize with price data
        
        Args:
            data: DataFrame with 'Gold' and 'Nifty' columns, datetime index
        """
        self.data = data.copy()
        self.regime_history = None
        
    def calculate_indicators(self):
        """Calculate all technical indicators"""
        df = self.data.copy()
        
        # 1. Gold/Nifty Ratio
        df['Ratio'] = df['Gold'] / df['Nifty']
        df['Ratio_MA50'] = df['Ratio'].rolling(window=50).mean()
        df['Ratio_MA200'] = df['Ratio'].rolling(window=200).mean()
        
        # 2. Moving Averages for trend detection
        df['Gold_MA50'] = df['Gold'].rolling(window=50).mean()
        df['Gold_MA200'] = df['Gold'].rolling(window=200).mean()
        df['Nifty_MA50'] = df['Nifty'].rolling(window=50).mean()
        df['Nifty_MA200'] = df['Nifty'].rolling(window=200).mean()
        
        # 3. Trend signals
        df['Gold_Uptrend'] = df['Gold'] > df['Gold_MA50']
        df['Nifty_Uptrend'] = df['Nifty'] > df['Nifty_MA50']
        
        # 4. Ratio trend
        df['Ratio_Above_MA'] = df['Ratio'] > df['Ratio_MA50']
        
        # 5. RSI for exit signals
        df['Gold_RSI'] = self._calculate_rsi(df['Gold'], 14)
        df['Nifty_RSI'] = self._calculate_rsi(df['Nifty'], 14)
        
        # 6. Rate of Change (ROC)
        df['Gold_ROC'] = df['Gold'].pct_change(14) * 100
        df['Nifty_ROC'] = df['Nifty'].pct_change(14) * 100
        
        # 7. Correlation (rolling 20-day)
        df['Correlation'] = df['Gold'].pct_change().rolling(20).corr(df['Nifty'].pct_change())
        
        self.data = df
        return df
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def identify_regimes(self):
        """
        Identify 4 market regimes:
        1. RISK-ON: Nifty up, Gold flat/down, Ratio down
        2. RISK-OFF: Gold up, Nifty flat/down, Ratio up
        3. STRESS: Both down
        4. LIQUIDITY BOOM: Both up
        """
        df = self.data.copy()
        
        def classify_regime(row):
            nifty_up = row['Nifty_Uptrend']
            gold_up = row['Gold_Uptrend']
            ratio_up = row['Ratio_Above_MA']
            
            # STRESS: Both falling
            if not nifty_up and not gold_up:
                return 'STRESS'
            
            # LIQUIDITY BOOM: Both rising
            elif nifty_up and gold_up:
                return 'LIQUIDITY_BOOM'
            
            # RISK-OFF: Gold up, Nifty down, Ratio rising
            elif gold_up and not nifty_up and ratio_up:
                return 'RISK_OFF'
            
            # RISK-ON: Nifty up, Gold down/flat, Ratio falling
            elif nifty_up and not gold_up and not ratio_up:
                return 'RISK_ON'
            
            # RISK-ON: Nifty up, Ratio falling
            elif nifty_up and not ratio_up:
                return 'RISK_ON'
            
            # RISK-OFF: Gold up, Ratio rising
            elif gold_up and ratio_up:
                return 'RISK_OFF'
            
            # Default based on ratio
            elif ratio_up:
                return 'RISK_OFF'
            else:
                return 'RISK_ON'
        
        df['Regime'] = df.apply(classify_regime, axis=1)
        
        self.data = df
        return df
    
    def generate_exit_signals(self):
        """Generate exit signals for both Equity and Gold"""
        df = self.data.copy()
        
        # EQUITY EXIT SIGNALS
        # Level 1: Warning
        df['Equity_Exit_L1'] = (
            (df['Nifty_RSI'] > 70) & 
            (df['Ratio'] > df['Ratio_MA50'])
        ) | (df['Regime'] == 'RISK_OFF')
        
        # Level 2: Strong exit
        df['Equity_Exit_L2'] = (
            df['Equity_Exit_L1'] & 
            (df['Nifty'] < df['Nifty_MA50']) &
            (df['Gold_Uptrend'])
        )
        
        # Level 3: Full exit (STRESS regime)
        df['Equity_Exit_L3'] = (df['Regime'] == 'STRESS')
        
        # GOLD EXIT SIGNALS
        # Level 1: Warning
        df['Gold_Exit_L1'] = (
            (df['Gold_RSI'] > 75) & 
            (df['Ratio'] < df['Ratio_MA50'])
        ) | (df['Regime'] == 'RISK_ON')
        
        # Level 2: Strong exit
        df['Gold_Exit_L2'] = (
            df['Gold_Exit_L1'] & 
            (df['Gold'] < df['Gold_MA50']) &
            (df['Nifty_Uptrend'])
        )
        
        # Level 3: Full exit
        df['Gold_Exit_L3'] = (
            (df['Regime'] == 'RISK_ON') &
            (df['Gold'] < df['Gold_MA200'])
        )
        
        self.data = df
        return df
    
    def backtest_performance(self):
        """Backtest regime-based strategy performance"""
        df = self.data.copy()
        
        # Calculate returns
        df['Nifty_Return'] = df['Nifty'].pct_change()
        df['Gold_Return'] = df['Gold'].pct_change()
        
        # Strategy: Switch based on regime
        def get_strategy_return(row):
            if pd.isna(row['Regime']):
                return 0
            if row['Regime'] == 'RISK_ON':
                return row['Nifty_Return']
            elif row['Regime'] == 'RISK_OFF':
                return row['Gold_Return']
            elif row['Regime'] == 'LIQUIDITY_BOOM':
                return (row['Nifty_Return'] + row['Gold_Return']) / 2
                # return row['Nifty_Return'] # Prefer equities in boom
            else:  # STRESS
                return 0  # Cash
        
        df['Strategy_Return'] = df.apply(get_strategy_return, axis=1)
        
        # Cumulative returns
        df['Nifty_Cumulative'] = (1 + df['Nifty_Return']).cumprod()
        df['Gold_Cumulative'] = (1 + df['Gold_Return']).cumprod()
        df['Strategy_Cumulative'] = (1 + df['Strategy_Return']).cumprod()
        
        # 60/40 Portfolio
        df['Portfolio_60_40_Return'] = 0.6 * df['Nifty_Return'] + 0.4 * df['Gold_Return']
        df['Portfolio_60_40_Cumulative'] = (1 + df['Portfolio_60_40_Return']).cumprod()
        
        self.data = df
        return df
    
    def analyze_regime_statistics(self):
        """Generate detailed statistics for each regime"""
        df = self.data.copy()
        
        stats = []
        for regime in ['RISK_ON', 'RISK_OFF', 'STRESS', 'LIQUIDITY_BOOM']:
            regime_df = df[df['Regime'] == regime]
            
            if len(regime_df) == 0:
                continue
            
            stats.append({
                'Regime': regime,
                'Days': len(regime_df),
                'Percentage': len(regime_df) / len(df) * 100,
                'Avg_Nifty_Return_%': regime_df['Nifty_Return'].mean() * 100,
                'Avg_Gold_Return_%': regime_df['Gold_Return'].mean() * 100,
                'Nifty_Volatility_%': regime_df['Nifty_Return'].std() * np.sqrt(252) * 100,
                'Gold_Volatility_%': regime_df['Gold_Return'].std() * np.sqrt(252) * 100
            })
        
        return pd.DataFrame(stats)
    
    def get_regime_changes(self):
        """Get all regime change dates"""
        df = self.data.copy()
        regime_changes = df[df['Regime'] != df['Regime'].shift(1)].copy()
        regime_changes['Previous_Regime'] = df['Regime'].shift(1)
        return regime_changes[['Regime', 'Previous_Regime', 'Nifty', 'Gold', 'Ratio']]
    
    def get_current_status(self):
        """Get current regime and relevant metrics"""
        latest = self.data.iloc[-1]
        
        # Find when current regime started
        current_regime = latest['Regime']
        regime_start_idx = None
        
        for i in range(len(self.data) - 1, -1, -1):
            if self.data.iloc[i]['Regime'] != current_regime:
                regime_start_idx = i + 1
                break
        
        if regime_start_idx is None:
            regime_start_idx = 0
        
        regime_start_date = self.data.index[regime_start_idx]
        days_in_regime = len(self.data) - regime_start_idx
        
        # Calculate returns since regime started
        start_nifty = self.data.iloc[regime_start_idx]['Nifty']
        start_gold = self.data.iloc[regime_start_idx]['Gold']
        
        nifty_change = ((latest['Nifty'] - start_nifty) / start_nifty) * 100
        gold_change = ((latest['Gold'] - start_gold) / start_gold) * 100
        
        # Determine recommended allocation
        allocation = self._get_allocation_recommendation(current_regime)
        
        return {
            'current_regime': current_regime,
            'regime_start_date': regime_start_date.strftime('%Y-%m-%d'),
            'days_in_regime': days_in_regime,
            'current_nifty': float(latest['Nifty']),
            'current_gold': float(latest['Gold']),
            'current_ratio': float(latest['Ratio']),
            'nifty_change_pct': float(nifty_change),
            'gold_change_pct': float(gold_change),
            'nifty_rsi': float(latest['Nifty_RSI']) if not pd.isna(latest['Nifty_RSI']) else None,
            'gold_rsi': float(latest['Gold_RSI']) if not pd.isna(latest['Gold_RSI']) else None,
            'correlation': float(latest['Correlation']) if not pd.isna(latest['Correlation']) else None,
            'equity_exit_l1': bool(latest['Equity_Exit_L1']),
            'equity_exit_l2': bool(latest['Equity_Exit_L2']),
            'equity_exit_l3': bool(latest['Equity_Exit_L3']),
            'gold_exit_l1': bool(latest['Gold_Exit_L1']),
            'gold_exit_l2': bool(latest['Gold_Exit_L2']),
            'gold_exit_l3': bool(latest['Gold_Exit_L3']),
            'recommended_allocation': allocation,
            'last_updated': self.data.index[-1].strftime('%Y-%m-%d')
        }
    
    def _get_allocation_recommendation(self, regime):
        """Get recommended asset allocation for regime"""
        allocations = {
            'RISK_ON': {
                'nifty_pct': 70,
                'gold_pct': 20,
                'cash_pct': 10,
                'description': 'Favor equities - market in risk-on mode'
            },
            'RISK_OFF': {
                'nifty_pct': 30,
                'gold_pct': 60,
                'cash_pct': 10,
                'description': 'Favor gold - defensive positioning'
            },
            'STRESS': {
                'nifty_pct': 0,
                'gold_pct': 0,
                'cash_pct': 100,
                'description': 'Move to cash - both assets declining'
            },
            'LIQUIDITY_BOOM': {
                'nifty_pct': 60,
                'gold_pct': 30,
                'cash_pct': 10,
                'description': 'Both assets rising - prefer equities'
            }
        }
        return allocations.get(regime, allocations['RISK_ON'])
    
    def get_performance_metrics(self):
        """Calculate comprehensive performance metrics"""
        df = self.data.copy()
        
        # Total returns
        final_nifty = (df['Nifty_Cumulative'].iloc[-1] - 1) * 100
        final_gold = (df['Gold_Cumulative'].iloc[-1] - 1) * 100
        final_strategy = (df['Strategy_Cumulative'].iloc[-1] - 1) * 100
        final_portfolio = (df['Portfolio_60_40_Cumulative'].iloc[-1] - 1) * 100
        
        # Annualized returns
        years = (df.index[-1] - df.index[0]).days / 365.25
        annual_nifty = ((1 + final_nifty/100) ** (1/years) - 1) * 100
        annual_gold = ((1 + final_gold/100) ** (1/years) - 1) * 100
        annual_strategy = ((1 + final_strategy/100) ** (1/years) - 1) * 100
        annual_portfolio = ((1 + final_portfolio/100) ** (1/years) - 1) * 100
        
        # Volatility
        nifty_vol = df['Nifty_Return'].std() * np.sqrt(252) * 100
        gold_vol = df['Gold_Return'].std() * np.sqrt(252) * 100
        strategy_vol = df['Strategy_Return'].std() * np.sqrt(252) * 100
        portfolio_vol = df['Portfolio_60_40_Return'].std() * np.sqrt(252) * 100
        
        # Sharpe Ratio (assuming 6% risk-free rate)
        rf = 0.06
        sharpe_nifty = (annual_nifty/100 - rf) / (nifty_vol/100) if nifty_vol > 0 else 0
        sharpe_gold = (annual_gold/100 - rf) / (gold_vol/100) if gold_vol > 0 else 0
        sharpe_strategy = (annual_strategy/100 - rf) / (strategy_vol/100) if strategy_vol > 0 else 0
        sharpe_portfolio = (annual_portfolio/100 - rf) / (portfolio_vol/100) if portfolio_vol > 0 else 0
        
        # Max Drawdown
        def calculate_max_drawdown(cumulative_returns):
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max * 100
            return drawdown.min()
        
        dd_nifty = calculate_max_drawdown(df['Nifty_Cumulative'])
        dd_gold = calculate_max_drawdown(df['Gold_Cumulative'])
        dd_strategy = calculate_max_drawdown(df['Strategy_Cumulative'])
        dd_portfolio = calculate_max_drawdown(df['Portfolio_60_40_Cumulative'])
        
        return {
            'period_years': round(years, 2),
            'total_returns': {
                'nifty': round(final_nifty, 2),
                'gold': round(final_gold, 2),
                'regime_strategy': round(final_strategy, 2),
                'portfolio_60_40': round(final_portfolio, 2)
            },
            'annualized_returns': {
                'nifty': round(annual_nifty, 2),
                'gold': round(annual_gold, 2),
                'regime_strategy': round(annual_strategy, 2),
                'portfolio_60_40': round(annual_portfolio, 2)
            },
            'volatility': {
                'nifty': round(nifty_vol, 2),
                'gold': round(gold_vol, 2),
                'regime_strategy': round(strategy_vol, 2),
                'portfolio_60_40': round(portfolio_vol, 2)
            },
            'sharpe_ratio': {
                'nifty': round(sharpe_nifty, 2),
                'gold': round(sharpe_gold, 2),
                'regime_strategy': round(sharpe_strategy, 2),
                'portfolio_60_40': round(sharpe_portfolio, 2)
            },
            'max_drawdown': {
                'nifty': round(dd_nifty, 2),
                'gold': round(dd_gold, 2),
                'regime_strategy': round(dd_strategy, 2),
                'portfolio_60_40': round(dd_portfolio, 2)
            }
        }
    
    def run_analysis(self):
        """Run complete analysis pipeline"""
        self.calculate_indicators()
        self.identify_regimes()
        self.generate_exit_signals()
        self.backtest_performance()
        return self.data


# Example usage
if __name__ == "__main__":
    # This would normally come from DataFetcher
    # Here we just demonstrate the API
    print("RegimeAnalyzer is a pure analysis module.")
    print("Use DataFetcher to get data, then pass to RegimeAnalyzer.")
    print("Example:")
    print("  from data_fetcher import DataFetcher")
    print("  from regime_analyzer import RegimeAnalyzer")
    print("  ")
    print("  fetcher = DataFetcher()")
    print("  data = fetcher.fetch_data()")
    print("  analyzer = RegimeAnalyzer(data)")
    print("  analyzer.run_analysis()")
    print("  status = analyzer.get_current_status()")
