"""
Example Usage Script
Demonstrates how to use the modular regime analysis system
"""

from data_fetcher import DataFetcher
from regime_analyzer import RegimeAnalyzer
import pandas as pd


def example_1_basic_usage():
    """Basic usage: Fetch data and get current regime"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage")
    print("="*80)
    
    # Fetch data (will use cache if available)
    fetcher = DataFetcher()
    data = fetcher.fetch_data(start_date='2020-01-01')
    
    print(f"\nData fetched: {len(data)} days")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    
    # Analyze
    analyzer = RegimeAnalyzer(data)
    analyzer.run_analysis()
    
    # Get current status
    status = analyzer.get_current_status()
    
    print(f"\n🎯 Current Regime: {status['current_regime']}")
    print(f"📅 Regime Started: {status['regime_start_date']}")
    print(f"📊 Days in Regime: {status['days_in_regime']}")
    print(f"\n💹 Current Prices:")
    print(f"   Nifty: ₹{status['current_nifty']:,.0f} ({status['nifty_change_pct']:+.2f}% in regime)")
    print(f"   Gold:  ${status['current_gold']:,.0f} ({status['gold_change_pct']:+.2f}% in regime)")
    
    print(f"\n📊 Recommended Allocation:")
    alloc = status['recommended_allocation']
    print(f"   Nifty: {alloc['nifty_pct']}%")
    print(f"   Gold:  {alloc['gold_pct']}%")
    print(f"   Cash:  {alloc['cash_pct']}%")
    print(f"   📝 {alloc['description']}")


def example_2_performance_metrics():
    """Get performance metrics"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Performance Metrics")
    print("="*80)
    
    fetcher = DataFetcher()
    data = fetcher.fetch_data(start_date='2016-01-01')
    
    analyzer = RegimeAnalyzer(data)
    analyzer.run_analysis()
    
    metrics = analyzer.get_performance_metrics()
    
    print(f"\n📊 Analysis Period: {metrics['period_years']} years")
    
    print("\n💰 Total Returns:")
    for strategy, return_val in metrics['total_returns'].items():
        print(f"   {strategy:20s}: {return_val:>8.2f}%")
    
    print("\n📈 Annualized Returns:")
    for strategy, return_val in metrics['annualized_returns'].items():
        print(f"   {strategy:20s}: {return_val:>8.2f}%")
    
    print("\n⚡ Sharpe Ratios:")
    for strategy, sharpe in metrics['sharpe_ratio'].items():
        print(f"   {strategy:20s}: {sharpe:>8.2f}")


def example_3_regime_statistics():
    """Analyze each regime type"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Regime Statistics")
    print("="*80)
    
    fetcher = DataFetcher()
    data = fetcher.fetch_data(start_date='2016-01-01')
    
    analyzer = RegimeAnalyzer(data)
    analyzer.run_analysis()
    
    stats = analyzer.analyze_regime_statistics()
    
    print("\n📊 Statistics by Regime:")
    print(stats.to_string(index=False))


def example_4_regime_history():
    """Get regime change history"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Recent Regime Changes")
    print("="*80)
    
    fetcher = DataFetcher()
    data = fetcher.fetch_data(start_date='2020-01-01')
    
    analyzer = RegimeAnalyzer(data)
    analyzer.run_analysis()
    
    changes = analyzer.get_regime_changes()
    
    print(f"\nLast 10 Regime Changes:")
    recent = changes.tail(10)
    
    for idx, row in recent.iterrows():
        print(f"{idx.date()}: → {row['Regime']:15s} (Nifty: ₹{row['Nifty']:>8,.0f}, Gold: ${row['Gold']:>6,.0f})")


def example_5_cache_management():
    """Demonstrate cache functionality"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Cache Management")
    print("="*80)
    
    fetcher = DataFetcher()
    
    # Get cache info
    info = fetcher.get_cache_info()
    
    if info['exists']:
        print("\n✅ Cache exists:")
        print(f"   Location: {info['path']}")
        print(f"   Rows: {info['rows']}")
        print(f"   Date range: {info['start_date']} to {info['end_date']}")
        print(f"   Size: {info['size_mb']:.2f} MB")
    else:
        print("\n❌ No cache found")
        print(f"   Expected location: {info['path']}")
    
    # Demonstrate force refresh
    print("\n🔄 Fetching data (will use cache if available)...")
    data1 = fetcher.fetch_data(start_date='2020-01-01')
    print(f"   Fetched {len(data1)} rows")
    
    print("\n🔄 Fetching again (should be instant from cache)...")
    data2 = fetcher.fetch_data(start_date='2020-01-01')
    print(f"   Fetched {len(data2)} rows")
    
    # Option to clear cache
    # fetcher.clear_cache()
    # print("\n🗑️  Cache cleared")


def example_6_export_data():
    """Export analyzed data to CSV"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Export Data")
    print("="*80)
    
    fetcher = DataFetcher()
    data = fetcher.fetch_data(start_date='2020-01-01')
    
    analyzer = RegimeAnalyzer(data)
    analyzer.run_analysis()
    
    # Export full data
    output_file = 'regime_analysis_output.csv'
    analyzer.data.to_csv(output_file)
    
    print(f"\n✅ Data exported to: {output_file}")
    print(f"   Rows: {len(analyzer.data)}")
    print(f"   Columns: {len(analyzer.data.columns)}")
    print(f"\n   Columns include:")
    for col in analyzer.data.columns[:10]:
        print(f"      - {col}")
    if len(analyzer.data.columns) > 10:
        print(f"      ... and {len(analyzer.data.columns) - 10} more")


def example_7_custom_date_range():
    """Use custom date ranges"""
    print("\n" + "="*80)
    print("EXAMPLE 7: Custom Date Ranges")
    print("="*80)
    
    fetcher = DataFetcher()
    
    # Fetch specific period
    print("\n📅 Fetching data for 2023 only...")
    data = fetcher.fetch_data(
        start_date='2023-01-01',
        end_date='2023-12-31'
    )
    
    analyzer = RegimeAnalyzer(data)
    analyzer.run_analysis()
    
    print(f"   Data range: {data.index[0].date()} to {data.index[-1].date()}")
    print(f"   Trading days: {len(data)}")
    
    # Get metrics for this period
    metrics = analyzer.get_performance_metrics()
    print(f"\n📊 2023 Performance:")
    print(f"   Nifty: {metrics['total_returns']['nifty']:.2f}%")
    print(f"   Gold: {metrics['total_returns']['gold']:.2f}%")
    print(f"   Strategy: {metrics['total_returns']['regime_strategy']:.2f}%")


def run_all_examples():
    """Run all examples"""
    examples = [
        example_1_basic_usage,
        example_2_performance_metrics,
        example_3_regime_statistics,
        example_4_regime_history,
        example_5_cache_management,
        example_6_export_data,
        example_7_custom_date_range
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ Error in {example.__name__}: {e}")
        
        print("\n" + "-"*80)
        input("Press Enter to continue to next example...")


if __name__ == "__main__":
    print("\n" + "="*80)
    print(" GOLD/NIFTY REGIME ANALYZER - USAGE EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates various ways to use the regime analysis system.")
    print("\nOptions:")
    print("  1. Run all examples (interactive)")
    print("  2. Run specific example")
    print("  3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        run_all_examples()
    elif choice == "2":
        print("\nAvailable examples:")
        print("  1. Basic Usage")
        print("  2. Performance Metrics")
        print("  3. Regime Statistics")
        print("  4. Regime History")
        print("  5. Cache Management")
        print("  6. Export Data")
        print("  7. Custom Date Ranges")
        
        ex_choice = input("\nEnter example number (1-7): ").strip()
        
        examples = {
            "1": example_1_basic_usage,
            "2": example_2_performance_metrics,
            "3": example_3_regime_statistics,
            "4": example_4_regime_history,
            "5": example_5_cache_management,
            "6": example_6_export_data,
            "7": example_7_custom_date_range
        }
        
        if ex_choice in examples:
            examples[ex_choice]()
        else:
            print("Invalid choice")
    
    print("\n✅ Done!")
