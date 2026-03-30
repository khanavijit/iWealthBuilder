from app.models.sip import SIPDefinition
from app.database import DBSIPDefinition, DBInvestment, get_db_session
from sqlalchemy.orm import Session
from sqlalchemy import and_


# Utility to map DB model to Pydantic model
def map_db_to_pydantic_sip(db_sip: DBSIPDefinition) -> SIPDefinition:
    """Converts a DBSIPDefinition object to a SIPDefinition Pydantic model."""
    return SIPDefinition(
        id=db_sip.id,
        investment_name=db_sip.investment_name,
        amount=db_sip.amount,
        frequency=db_sip.frequency,
        start_date=db_sip.start_date,
        status=db_sip.status
    )


def create_sip_definition(sip_data: SIPDefinition, session: Session = next(get_db_session())) -> SIPDefinition:
    """Adds a new SIP definition to the database."""

    # Find the corresponding investment ID
    db_inv = session.query(DBInvestment).filter(DBInvestment.name == sip_data.investment_name).first()
    if not db_inv:
        raise ValueError(f"Investment '{sip_data.investment_name}' not found.")

    # Check for duplicates (same investment, same frequency, active status)
    existing_sip = session.query(DBSIPDefinition).filter(
        and_(
            DBSIPDefinition.investment_id == db_inv.id,
            DBSIPDefinition.frequency == sip_data.frequency,
            DBSIPDefinition.status == "Active"
        )
    ).first()

    if existing_sip:
        raise ValueError(f"An active {sip_data.frequency} SIP already exists for '{sip_data.investment_name}'.")

    # Insert new SIP definition
    new_db_sip = DBSIPDefinition(
        investment_id=db_inv.id,
        investment_name=sip_data.investment_name,
        amount=sip_data.amount,
        frequency=sip_data.frequency,
        start_date=sip_data.start_date,
        status=sip_data.status
    )

    session.add(new_db_sip)
    session.commit()
    session.refresh(new_db_sip)

    return map_db_to_pydantic_sip(new_db_sip)


def get_all_sip_definitions(session: Session = next(get_db_session())) -> list[SIPDefinition]:
    """Retrieves all stored SIP definitions."""
    db_sips = session.query(DBSIPDefinition).all()
    return [map_db_to_pydantic_sip(db_sip) for db_sip in db_sips]


def update_sip_status(sip_id: int, new_status: str, session: Session = next(get_db_session())) -> SIPDefinition:
    """Updates the status of an existing SIP (e.g., Pause)."""
    db_sip = session.query(DBSIPDefinition).filter(DBSIPDefinition.id == sip_id).first()

    if not db_sip:
        raise ValueError(f"SIP with ID {sip_id} not found.")

    db_sip.status = new_status
    session.add(db_sip)
    session.commit()
    session.refresh(db_sip)

    return map_db_to_pydantic_sip(db_sip)