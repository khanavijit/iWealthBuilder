from fastapi import APIRouter, HTTPException
from app.models.sip import SIPDefinition
from app.services import sip_service
from typing import Dict, Any

router = APIRouter(
    prefix="/sips",
    tags=["SIP Management"]
)

@router.post("/add")
def add_sip_definition(sip_data: SIPDefinition):
    """Endpoint to define a new SIP schedule."""
    try:
        new_sip = sip_service.create_sip_definition(sip_data)
        return {"message": f"SIP definition for '{new_sip.investment_name}' added successfully.", "data": new_sip.model_dump(by_alias=True, mode='json')}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add SIP definition: {e}")

@router.put("/status/{sip_id}")
def update_sip_status(sip_id: int, new_status: str):
    """Endpoint to update the status of a SIP (e.g., Pause/Activate)."""
    try:
        updated_sip = sip_service.update_sip_status(sip_id, new_status)
        return {"message": f"SIP {sip_id} status updated to '{new_status}'.", "data": updated_sip.model_dump(by_alias=True, mode='json')}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update SIP status: {e}")