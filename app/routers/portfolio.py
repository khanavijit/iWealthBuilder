from fastapi import APIRouter, Depends, HTTPException
from app.services import investment_service
from app.models.investment import Investment
from app.services import sip_service
from app.models.sip import SIPDefinition
from typing import Dict, Any, List

router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio Data"]
)


@router.get("/data")
def get_full_portfolio_data() -> Dict[str, Any]:
    """Retrieves all investment data, metrics, and summary."""
    try:
        investments_dict = investment_service.get_all_investments_with_metrics()
        summary = investment_service.get_portfolio_summary(investments_dict)

        # Convert Investment models to a serializable dictionary
        investments_data = {
            name: inv.model_dump(by_alias=True, mode='json')
            for name, inv in investments_dict.items()
        }

        # Also fetch and include SIP definitions
        sip_definitions = sip_service.get_all_sip_definitions()

        return {
            "summary": summary,
            "investments": investments_data,
            "sips": [sip.model_dump(by_alias=True, mode='json') for sip in sip_definitions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")