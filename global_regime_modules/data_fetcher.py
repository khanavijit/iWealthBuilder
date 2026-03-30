"""
Data Fetcher with Intelligent Caching
Fetches Gold and Nifty data from Yahoo Finance
Only downloads new data if cache exists
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
from pathlib import Path


class DataFetcher:
    """Fetches and caches Gold and Nifty data"""
    
    def __init__(self, cache_file='data_cache.csv'):
        self.cache_file = cache_file
        self.cache_dir = Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_path = self.cache_dir / cache_file
        
    def fetch_data(self, start_date='2016-01-01', end_date=None, force_refresh=False):
        """
        Fetch data with intelligent caching
        
        Args:
            start_date: Start date for data (YYYY-MM-DD)
            end_date: End date for data (YYYY-MM-DD), defaults to today
            force_refresh: If True, ignore cache and fetch all data fresh
            
        Returns:
            DataFrame with Gold and Nifty prices
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if cache exists and we're not forcing refresh
        if not force_refresh and self.cache_path.exists():
            print(f"📦 Cache found at: {self.cache_path}")
            return self._update_cached_data(start_date, end_date)
        else:
            print("🌐 No cache found or force refresh requested. Fetching all data...")
            return self._fetch_fresh_data(start_date, end_date)
    
    def _fetch_fresh_data(self, start_date, end_date):
        """Fetch all data fresh from Yahoo Finance"""
        print(f"⏳ Fetching data from {start_date} to {end_date}...")
        
        # Fetch Gold (GC=F is Gold Futures)
        print("  Downloading Gold data...")
        gold = yf.download('GC=F', start=start_date, end=end_date, 
                          progress=False, auto_adjust=True, multi_level_index=False)
        
        # Fetch Nifty 50 (^NSEI)
        print("  Downloading Nifty data...")
        nifty = yf.download('^NSEI', start=start_date, end=end_date, 
                           progress=False, auto_adjust=True, multi_level_index=False)
        
        # Create combined dataframe
        df = pd.DataFrame({
            'Gold': gold['Close'],
            'Nifty': nifty['Close']
        })
        
        # Forward fill missing values (different trading days)
        df = df.fillna(method='ffill').dropna()
        
        # Save to cache
        df.to_csv(self.cache_path)
        print(f"💾 Data cached to: {self.cache_path}")
        print(f"✅ Fetched {len(df)} trading days from {df.index[0].date()} to {df.index[-1].date()}")
        
        return df
    
    def _update_cached_data(self, start_date, end_date):
        """Update cache with only new data"""
        # Load cached data
        cached_df = pd.read_csv(self.cache_path, index_col=0, parse_dates=True)
        print(f"  Cached data: {len(cached_df)} days ({cached_df.index[0].date()} to {cached_df.index[-1].date()})")
        
        # Determine if we need new data
        last_cached_date = cached_df.index[-1]
        end_date_dt = pd.to_datetime(end_date)
        
        # Check if we need to fetch earlier data (start_date before cache)
        start_date_dt = pd.to_datetime(start_date)
        first_cached_date = cached_df.index[0]
        
        need_earlier_data = start_date_dt < first_cached_date
        need_newer_data = end_date_dt > last_cached_date
        
        if not need_earlier_data and not need_newer_data:
            print("✅ Cache is up to date! Using cached data.")
            # Return subset based on requested date range
            mask = (cached_df.index >= start_date_dt) & (cached_df.index <= end_date_dt)
            return cached_df.loc[mask]
        
        # Fetch missing data
        new_data_parts = []
        
        if need_earlier_data:
            print(f"📥 Fetching earlier data: {start_date} to {first_cached_date.date()}...")
            earlier_data = self._fetch_date_range(start_date, first_cached_date.strftime('%Y-%m-%d'))
            if not earlier_data.empty:
                new_data_parts.append(earlier_data)
        
        if need_newer_data:
            # Fetch from day after last cached date
            fetch_start = (last_cached_date + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"📥 Fetching newer data: {fetch_start} to {end_date}...")
            newer_data = self._fetch_date_range(fetch_start, end_date)
            if not newer_data.empty:
                new_data_parts.append(newer_data)
        
        # Combine all data
        all_parts = new_data_parts + [cached_df]
        combined_df = pd.concat(all_parts).sort_index()
        
        # Remove duplicates, keep last
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        
        # Save updated cache
        combined_df.to_csv(self.cache_path)
        print(f"💾 Updated cache saved")
        print(f"✅ Total data: {len(combined_df)} days ({combined_df.index[0].date()} to {combined_df.index[-1].date()})")
        
        # Return subset based on requested date range
        mask = (combined_df.index >= start_date_dt) & (combined_df.index <= end_date_dt)
        return combined_df.loc[mask]
    
    def _fetch_date_range(self, start, end):
        """Fetch data for a specific date range"""
        try:
            # Fetch Gold
            gold = yf.download('GC=F', start=start, end=end, 
                             progress=False, auto_adjust=True, multi_level_index=False)
            
            # Fetch Nifty
            nifty = yf.download('^NSEI', start=start, end=end, 
                              progress=False, auto_adjust=True, multi_level_index=False)
            
            # Combine
            df = pd.DataFrame({
                'Gold': gold['Close'],
                'Nifty': nifty['Close']
            })
            
            # Forward fill and clean
            df = df.fillna(method='ffill').dropna()
            
            return df
            
        except Exception as e:
            print(f"⚠️  Error fetching data for {start} to {end}: {e}")
            return pd.DataFrame()
    
    def clear_cache(self):
        """Delete the cache file"""
        if self.cache_path.exists():
            self.cache_path.unlink()
            print(f"🗑️  Cache deleted: {self.cache_path}")
        else:
            print("ℹ️  No cache file to delete")
    
    def get_cache_info(self):
        """Get information about the cache"""
        if not self.cache_path.exists():
            return {
                'exists': False,
                'path': str(self.cache_path)
            }
        
        df = pd.read_csv(self.cache_path, index_col=0, parse_dates=True)
        
        return {
            'exists': True,
            'path': str(self.cache_path),
            'rows': len(df),
            'start_date': str(df.index[0].date()),
            'end_date': str(df.index[-1].date()),
            'size_mb': self.cache_path.stat().st_size / (1024 * 1024)
        }


# Example usage
if __name__ == "__main__":
    fetcher = DataFetcher()
    
    # First run - will fetch all data
    print("\n" + "="*80)
    print("First fetch (will download all data)")
    print("="*80)
    df1 = fetcher.fetch_data(start_date='2020-01-01')
    print(f"\nData shape: {df1.shape}")
    print(f"Date range: {df1.index[0]} to {df1.index[-1]}")
    
    # Second run - will use cache and only fetch new data
    print("\n" + "="*80)
    print("Second fetch (will use cache)")
    print("="*80)
    df2 = fetcher.fetch_data(start_date='2020-01-01')
    print(f"\nData shape: {df2.shape}")
    
    # Cache info
    print("\n" + "="*80)
    print("Cache Information")
    print("="*80)
    info = fetcher.get_cache_info()
    for key, value in info.items():
        print(f"{key}: {value}")
