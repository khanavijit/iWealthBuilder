from fastapi import APIRouter, HTTPException
from app.models.investment import Investment, Transaction
from app.services import investment_service
from typing import Dict, Any

router = APIRouter(
    tags=["Transactions & Investments"]
)

@router.post("/investments/add")
def add_new_investment(inv_data: Investment):
    """Endpoint to define a new investment asset."""
    try:
        new_inv = investment_service.add_new_investment_asset(inv_data)
        return {"message": f"Investment asset '{new_inv.name}' created successfully.", "data": new_inv.model_dump(by_alias=True, mode='json')}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add investment: {e}")

@router.post("/transactions/add")
def add_new_transaction(txn_data: Transaction, investment_name: str):
    """Endpoint to add a transaction to an existing investment."""
    try:
        updated_inv = investment_service.add_transaction_to_investment(investment_name, txn_data)
        return {"message": f"Transaction added to '{investment_name}'.", "new_metrics": updated_inv.metrics.model_dump(by_alias=True, mode='json')}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add transaction: {e}")