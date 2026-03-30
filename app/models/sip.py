from pydantic import BaseModel, Field
from datetime import date
from typing import Optional # <--- ADD THIS IMPORT

class SIPDefinition(BaseModel):
    """Represents a definition/schedule for a Systematic Investment Plan (SIP)."""
    id: Optional[int] = None # Now resolves correctly
    investment_name: str
    amount: float = Field(..., gt=0, description="Amount invested per frequency")
    frequency: str = Field(..., description="e.g., 'Weekly', 'Monthly', 'Quarterly', 'One-Time'")
    start_date: date
    status: str = Field(default="Active", description="e.g., 'Active', 'Paused', 'Completed'")