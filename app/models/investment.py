from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class Transaction(BaseModel):
    """Represents a single buy or sell transaction."""
    date_str: date
    type_str: str = Field(..., description="Must be 'Buy' or 'Sell'")
    units: float = Field(..., gt=0, description="Number of units bought or sold")
    price: float = Field(..., gt=0, description="Price per unit")
    utc: float = 0.0 # Time offset for future use

class InvestmentMetrics(BaseModel):
    """Calculated metrics for an investment."""
    total_units: float = 0.0
    total_invested: float = 0.0
    market_value: float = 0.0
    absolute_return_percent: float = 0.0
    cagr: float = 0.0

class Investment(BaseModel):
    """Represents an investment asset (e.g., a stock, ETF, or fund)."""
    name: str = Field(..., description="Unique name of the asset")
    category: str = Field(..., description="Asset class (e.g., Equity, Bonds, MF)")
    risk_category: str = Field(..., description="Risk profile (e.g., Low, Medium, High)")
    initial_price: float = 100.0 # Current price, updated dynamically in a real app
    inv_type: str = "Flexible"
    transactions: List[Transaction] = Field(default_factory=list)
    metrics: InvestmentMetrics = Field(default_factory=InvestmentMetrics)