# investment_api.py

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import (
    SQLModel, Field, Relationship, create_engine, Session, select
)
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

# --- 1. Database Setup ---

sqlite_file_name = "investment.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# echo=True will print all SQL statements, useful for debugging
engine = create_engine(sqlite_url, echo=True)


def get_session():
    """
    FastAPI dependency to create and manage database sessions.
    """
    with Session(engine) as session:
        yield session


# --- 2. Enums for Model Choices ---

class AssetCategory(str, Enum):
    PF = "PF"
    PPF = "PPF"
    FD = "FD"
    MF = "MF"
    STOCK = "STOCK"
    DERIVATIVES = "DERIVATIVES"


class RiskCategory(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class SIPFrequency(str, Enum):
    NONE = "NONE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


# --- 3. SQLModel Definitions ---

# Forward declaration for relationships
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    investment_id: Optional[int] = Field(
        default=None, foreign_key="investment.id"
    )
    type: TransactionType
    date: datetime = Field(index=True)
    cash_amount: float

    # Unit-based fields
    units: Optional[float] = Field(default=None)
    price_per_unit: Optional[float] = Field(default=None)

    # For FIFO tracking on DEPOSITs
    units_remaining: Optional[float] = Field(default=None)

    # For WITHDRAWALs
    realized_pnl: float = Field(default=0.0)

    investment: Optional["Investment"] = Relationship(back_populates="transactions")


class Valuation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    investment_id: Optional[int] = Field(
        default=None, foreign_key="investment.id"
    )
    valuation_date: date = Field(index=True)
    current_price: float  # Current NAV or unit price

    investment: Optional["Investment"] = Relationship(back_populates="valuations")


class InvestmentBase(SQLModel):
    name: str = Field(index=True)
    asset_category: AssetCategory
    industry: str
    risk_category: RiskCategory
    sip_frequency: SIPFrequency
    status: Status = Field(default=Status.ACTIVE)


class Investment(InvestmentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # Enforce uniqueness

    transactions: List["Transaction"] = Relationship(
        back_populates="investment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    valuations: List["Valuation"] = Relationship(
        back_populates="investment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# --- 4. Pydantic Models for API (Input/Output) ---

class InvestmentCreate(InvestmentBase):
    pass


class InvestmentRead(InvestmentBase):
    id: int


class TransactionBase(SQLModel):
    type: TransactionType
    date: datetime
    cash_amount: float
    units: Optional[float] = None
    price_per_unit: Optional[float] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: int
    investment_id: int
    realized_pnl: float
    units_remaining: Optional[float]


class ValuationBase(SQLModel):
    valuation_date: date
    current_price: float


class ValuationCreate(ValuationBase):
    pass


class ValuationRead(ValuationBase):
    id: int
    investment_id: int


class PerformanceSummary(SQLModel):
    investment_name: str
    total_invested_capital: float
    total_withdrawn_capital: float
    total_realized_pnl: float
    total_units_held: float
    latest_unit_price: Optional[float]
    current_market_value: float
    unrealized_pnl: float


# --- 5. FIFO P&L Calculation Logic ---

def _calculate_fifo_pnl(
        session: Session,
        investment_id: int,
        units_to_sell: float,
        sale_cash_amount: float
) -> float:
    """
    Calculates realized P&L for a withdrawal using FIFO.
    This function modifies the 'units_remaining' on DEPOSIT transactions
    in the session.
    """

    # 1. Get all DEPOSIT transactions with units left, sorted by date (FIFO)
    statement = select(Transaction).where(
        Transaction.investment_id == investment_id,
        Transaction.type == TransactionType.DEPOSIT,
        Transaction.units_remaining > 0
    ).order_by(Transaction.date)

    deposits_with_units = session.exec(statement).all()

    # 2. Check if there are enough units to sell
    total_available_units = sum(
        d.units_remaining for d in deposits_with_units if d.units_remaining
    )
    if units_to_sell > total_available_units:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sell {units_to_sell} units. "
                   f"Only {total_available_units:.4f} units available."
        )

    # 3. Apply FIFO logic
    units_left_to_sell = units_to_sell
    total_cost_of_sold_units = 0.0

    for deposit in deposits_with_units:
        if units_left_to_sell <= 0:
            break

        # Check for None just in case, though query should prevent it
        if deposit.units_remaining is None or deposit.price_per_unit is None:
            continue

        units_from_this_deposit = min(deposit.units_remaining, units_left_to_sell)

        cost_of_these_units = units_from_this_deposit * deposit.price_per_unit
        total_cost_of_sold_units += cost_of_these_units

        # Update the deposit transaction
        deposit.units_remaining -= units_from_this_deposit
        units_left_to_sell -= units_from_this_deposit

        # Add the modified deposit to the session to be updated
        session.add(deposit)

    # 4. Calculate P&L
    realized_pnl = sale_cash_amount - total_cost_of_sold_units
    return realized_pnl


# --- 6. FastAPI Application and Endpoints ---

app = FastAPI(
    title="Personal Investment Tracker API",
    description="An API to track investments, transactions, and performance."
)


@app.on_event("startup")
def on_startup():
    """
    Creates all database tables on application startup.
    """
    SQLModel.metadata.create_all(engine)


@app.post("/investments/", response_model=InvestmentRead, tags=["Investments"])
def create_investment(
        investment: InvestmentCreate,
        session: Session = Depends(get_session)
):
    """
    Create a new investment record.
    """
    # Check for duplicate name
    existing = session.exec(
        select(Investment).where(Investment.name == investment.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Investment with name '{investment.name}' already exists."
        )

    db_investment = Investment.from_orm(investment)
    session.add(db_investment)
    session.commit()
    session.refresh(db_investment)
    return db_investment


@app.get("/investments/", response_model=List[InvestmentRead], tags=["Investments"])
def get_investments(session: Session = Depends(get_session)):
    """
    List all active investments.
    """
    statement = select(Investment).where(Investment.status == Status.ACTIVE)
    investments = session.exec(statement).all()
    return investments


@app.post(
    "/investments/{investment_id}/transactions",
    response_model=TransactionRead,
    tags=["Transactions & Performance"]
)
def create_transaction(
        investment_id: int,
        transaction: TransactionCreate,
        session: Session = Depends(get_session)
):
    """
    Log a new transaction (DEPOSIT or WITHDRAWAL).

    - If type is **WITHDRAWAL** for a unit-based asset (MF, STOCK, DERIVATIVES),
      this endpoint will automatically calculate the **realized P&L**
      using the **FIFO** method and update the cost basis of prior deposits.
    """
    db_investment = session.get(Investment, investment_id)
    if not db_investment:
        raise HTTPException(status_code=404, detail="Investment not found")

    # Assets that are tracked by units
    unit_based_assets = [
        AssetCategory.MF, AssetCategory.STOCK, AssetCategory.DERIVATIVES
    ]
    is_unit_based = db_investment.asset_category in unit_based_assets

    realized_pnl = 0.0

    # Create the base transaction object
    db_transaction = Transaction.from_orm(
        transaction,
        update={"investment_id": investment_id}
    )

    if is_unit_based:
        # Validate unit-based transactions
        if transaction.units is None or transaction.price_per_unit is None:
            raise HTTPException(
                status_code=400,
                detail="`units` and `price_per_unit` are mandatory "
                       "for MF, STOCK, or DERIVATIVES."
            )

        # Verify cash amount matches units * price
        if not abs(transaction.cash_amount -
                   (transaction.units * transaction.price_per_unit)) < 0.01:
            raise HTTPException(
                status_code=400,
                detail="`cash_amount` must equal `units` * `price_per_unit`."
            )

        if transaction.type == TransactionType.DEPOSIT:
            # For deposits, set initial units_remaining for FIFO
            db_transaction.units_remaining = transaction.units

        elif transaction.type == TransactionType.WITHDRAWAL:
            # Critical Logic: Calculate FIFO P&L
            realized_pnl = _calculate_fifo_pnl(
                session=session,
                investment_id=investment_id,
                units_to_sell=transaction.units,
                sale_cash_amount=transaction.cash_amount
            )
            db_transaction.realized_pnl = realized_pnl

    # For non-unit-based assets (FD, PPF, etc.), just log the transaction

    session.add(db_transaction)
    session.commit()

    # We refresh db_transaction to get the ID
    session.refresh(db_transaction)

    # Must commit *again* if _calculate_fifo_pnl modified other transactions
    session.commit()

    return db_transaction


@app.post(
    "/investments/{investment_id}/valuation",
    response_model=ValuationRead,
    tags=["Transactions & Performance"]
)
def create_valuation(
        investment_id: int,
        valuation: ValuationCreate,
        session: Session = Depends(get_session)
):
    """
    Record the latest market price/NAV for an investment.
    """
    db_investment = session.get(Investment, investment_id)
    if not db_investment:
        raise HTTPException(status_code=404, detail="Investment not found")

    db_valuation = Valuation.from_orm(
        valuation,
        update={"investment_id": investment_id}
    )
    session.add(db_valuation)
    session.commit()
    session.refresh(db_valuation)
    return db_valuation


@app.get(
    "/investments/{investment_id}/performance",
    response_model=PerformanceSummary,
    tags=["Transactions & Performance"]
)
def get_performance(
        investment_id: int,
        session: Session = Depends(get_session)
):
    """
    Get a full performance summary for a single investment, calculating
    realized P&L, unrealized P&L, and current market value.
    """
    db_investment = session.get(Investment, investment_id)
    if not db_investment:
        raise HTTPException(status_code=404, detail="Investment not found")

    # 1. Get all transactions
    tx_statement = select(Transaction).where(
        Transaction.investment_id == investment_id
    )
    all_transactions = session.exec(tx_statement).all()

    # 2. Get latest valuation
    val_statement = select(Valuation).where(
        Valuation.investment_id == investment_id
    ).order_by(Valuation.valuation_date.desc())
    latest_valuation = session.exec(val_statement).first()

    latest_unit_price = (
        latest_valuation.current_price if latest_valuation else 0.0
    )

    # 3. Calculate metrics
    total_invested_capital = 0.0
    total_withdrawn_capital = 0.0
    total_realized_pnl = 0.0
    total_units_held = 0.0

    is_unit_based = db_investment.asset_category in [
        AssetCategory.MF, AssetCategory.STOCK, AssetCategory.DERIVATIVES
    ]

    for tx in all_transactions:
        if tx.type == TransactionType.DEPOSIT:
            total_invested_capital += tx.cash_amount
            if is_unit_based and tx.units:
                total_units_held += tx.units

        elif tx.type == TransactionType.WITHDRAWAL:
            total_withdrawn_capital += tx.cash_amount
            total_realized_pnl += tx.realized_pnl
            if is_unit_based and tx.units:
                total_units_held -= tx.units

    # 4. Calculate derived metrics

    # Current Market Value (CMV)
    current_market_value = 0.0
    if is_unit_based:
        current_market_value = total_units_held * latest_unit_price
    else:
        # For non-unit assets, CMV is assumed to be the latest valuation price
        # (if provided), or just the net capital if not.
        if latest_valuation:
            current_market_value = latest_unit_price
            # This assumes price is total value, not unit price
            # A better model might have a 'total_value' field in Valuation
        else:
            # Fallback for non-unit-based with no valuation
            current_market_value = total_invested_capital - total_withdrawn_capital

    # Per the prompt's formula:
    # Unrealized P&L = CMV - (Invested - Withdrawn - Realized P&L)
    # This (Invested - Withdrawn - Realized P&L) represents the
    # "net cost basis" of the capital remaining in the investment.
    cost_basis_of_remaining_capital = (
            total_invested_capital - total_withdrawn_capital - total_realized_pnl
    )

    unrealized_pnl = current_market_value - cost_basis_of_remaining_capital

    # 5. Create response object
    return PerformanceSummary(
        investment_name=db_investment.name,
        total_invested_capital=total_invested_capital,
        total_withdrawn_capital=total_withdrawn_capital,
        total_realized_pnl=total_realized_pnl,
        total_units_held=total_units_held if is_unit_based else 0,
        latest_unit_price=latest_unit_price if is_unit_based else None,
        current_market_value=current_market_value,
        unrealized_pnl=unrealized_pnl
    )


# --- 7. Main Application Runner ---

if __name__ == "__main__":
    print("Starting Investment API server...")
    print(f"Database file: {sqlite_file_name}")
    # Note: create_db_and_tables() is called by the 'startup' event
    uvicorn.run(app, host="0.0.0.0", port=8000)