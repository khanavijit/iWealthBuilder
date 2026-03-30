"""
FastAPI Application for Gold/Nifty Regime Analysis
Provides REST API endpoints for regime data and analysis
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional
import uvicorn

from global_regime_modules.data_fetcher import DataFetcher
from global_regime_modules.regime_analyzer import RegimeAnalyzer

app = FastAPI(
    title="Gold/Nifty Regime Analysis API",
    description="API for analyzing market regimes based on Gold and Nifty performance",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global cache for analyzer
_analyzer_cache = {
    'analyzer': None,
    'last_update': None
}


def get_analyzer(force_refresh=False):
    """Get or create analyzer instance with caching"""
    global _analyzer_cache
    
    # Check if we need to refresh (data more than 1 day old or force refresh)
    needs_refresh = (
        force_refresh or 
        _analyzer_cache['analyzer'] is None or
        _analyzer_cache['last_update'] is None or
        (datetime.now() - _analyzer_cache['last_update']).days >= 1
    )
    
    if needs_refresh:
        # Fetch fresh data
        fetcher = DataFetcher()
        data = fetcher.fetch_data(start_date='2016-01-01')
        
        # Create analyzer
        analyzer = RegimeAnalyzer(data)
        analyzer.run_analysis()
        
        # Cache it
        _analyzer_cache['analyzer'] = analyzer
        _analyzer_cache['last_update'] = datetime.now()
    
    return _analyzer_cache['analyzer']


@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "Gold/Nifty Regime Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "current": "/api/current - Get current regime status",
            "regimes": "/api/regimes - Get all regime periods",
            "performance": "/api/performance - Get performance metrics",
            "regime_stats": "/api/regime-stats - Get statistics by regime",
            "data": "/api/data - Get historical data with regimes"
        }
    }


@app.get("/api/current")
def get_current_regime(refresh: bool = Query(False, description="Force refresh data")):
    """
    Get current market regime and related information
    
    Returns:
        - Current regime
        - When regime started
        - % movement in both assets since regime start
        - Recommended asset allocation
        - Exit signals
    """
    try:
        analyzer = get_analyzer(force_refresh=refresh)
        status = analyzer.get_current_status()
        
        return JSONResponse(content={
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/regimes")
def get_regime_history(
    limit: Optional[int] = Query(None, description="Limit number of regime periods returned"),
    regime_type: Optional[str] = Query(None, description="Filter by regime type")
):
    """
    Get historical regime periods
    
    Returns all regime change dates with associated metrics
    """
    try:
        analyzer = get_analyzer()
        regime_changes = analyzer.get_regime_changes()
        
        # Filter by regime type if specified
        if regime_type:
            regime_changes = regime_changes[
                regime_changes['Regime'].str.upper() == regime_type.upper()
            ]
        
        # Limit results if specified
        if limit:
            regime_changes = regime_changes.tail(limit)
        
        # Convert to dict
        result = regime_changes.reset_index().to_dict('records')
        
        # Format dates
        for item in result:
            if 'Date' in item:
                item['Date'] = pd.to_datetime(item['Date']).strftime('%Y-%m-%d')
        
        return JSONResponse(content={
            "status": "success",
            "count": len(result),
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance")
def get_performance_metrics(refresh: bool = Query(False)):
    """
    Get comprehensive performance metrics
    
    Returns:
        - Total returns for all strategies
        - Annualized returns
        - Volatility
        - Sharpe ratios
        - Maximum drawdowns
    """
    try:
        analyzer = get_analyzer(force_refresh=refresh)
        metrics = analyzer.get_performance_metrics()
        
        return JSONResponse(content={
            "status": "success",
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/regime-stats")
def get_regime_statistics(refresh: bool = Query(False)):
    """
    Get statistics for each regime type
    
    Returns average returns, volatility, and frequency for each regime
    """
    try:
        analyzer = get_analyzer(force_refresh=refresh)
        stats = analyzer.analyze_regime_statistics()
        
        result = stats.to_dict('records')
        
        return JSONResponse(content={
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data")
def get_historical_data(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(100, description="Number of recent days to return")
):
    """
    Get historical price data with regime classifications
    
    Returns daily data including:
        - Prices (Gold, Nifty)
        - Regime classification
        - Technical indicators
    """
    try:
        analyzer = get_analyzer()
        df = analyzer.data.copy()
        
        # Filter by date range if specified
        if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]
        
        # Limit to recent data if no date range specified
        if not start_date and not end_date and limit:
            df = df.tail(limit)
        
        # Select key columns
        columns = [
            'Gold', 'Nifty', 'Regime', 
            'Gold_MA50', 'Nifty_MA50',
            'Ratio', 'Ratio_MA50',
            'Gold_RSI', 'Nifty_RSI',
            'Correlation'
        ]
        
        df_export = df[columns].copy()
        df_export = df_export.reset_index()
        df_export['Date'] = df_export['Date'].dt.strftime('%Y-%m-%d')
        
        result = df_export.to_dict('records')
        
        return JSONResponse(content={
            "status": "success",
            "count": len(result),
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/allocation")
def get_allocation_recommendation(refresh: bool = Query(False)):
    """
    Get current recommended asset allocation
    
    Returns detailed allocation percentages for Nifty, Gold, and Cash
    based on current regime
    """
    try:
        analyzer = get_analyzer(force_refresh=refresh)
        status = analyzer.get_current_status()
        
        allocation = status['recommended_allocation']
        
        return JSONResponse(content={
            "status": "success",
            "data": {
                "current_regime": status['current_regime'],
                "allocation": allocation,
                "regime_details": {
                    "started": status['regime_start_date'],
                    "days_in_regime": status['days_in_regime'],
                    "nifty_change_pct": status['nifty_change_pct'],
                    "gold_change_pct": status['gold_change_pct']
                }
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refresh")
def refresh_data():
    """
    Force refresh of data from Yahoo Finance
    
    Clears cache and fetches latest data
    """
    try:
        global _analyzer_cache
        _analyzer_cache['analyzer'] = None
        _analyzer_cache['last_update'] = None
        
        # Force new fetch
        analyzer = get_analyzer(force_refresh=True)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Data refreshed successfully",
            "last_date": analyzer.data.index[-1].strftime('%Y-%m-%d'),
            "total_days": len(analyzer.data),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        analyzer = get_analyzer()
        return {
            "status": "healthy",
            "last_data_date": analyzer.data.index[-1].strftime('%Y-%m-%d'),
            "cache_age_hours": (datetime.now() - _analyzer_cache['last_update']).total_seconds() / 3600 if _analyzer_cache['last_update'] else None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Run the API
if __name__ == "__main__":
    port = 8085
    print("🚀 Starting Gold/Nifty Regime Analysis API...")
    print(f"📖 API Documentation: http://localhost:{port}/docs")
    print(f"🔍 Interactive API: http://localhost:{port}/redoc")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
