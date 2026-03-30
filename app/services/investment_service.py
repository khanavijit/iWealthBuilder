from app.models.investment import Investment, Transaction, InvestmentMetrics
from app.database import DBInvestment, DBTransaction, get_db_session
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Dict, Any, List
from datetime import datetime, date
import pandas as pd
import numpy as np


# Utility to map DB model to Pydantic model
def map_db_to_pydantic_investment(db_inv: DBInvestment) -> Investment:
    """Converts a DBInvestment object to an Investment Pydantic model."""
    txn_list = [
        Transaction(
            date_str=txn.date_str,
            type_str=txn.type_str,
            units=txn.units,
            price=txn.price,
            utc=txn.utc
        ) for txn in db_inv.transactions
    ]

    # Metrics stored as JSON are directly loaded
    metrics_data = db_inv.metrics if db_inv.metrics else {}

    return Investment(
        name=db_inv.name,
        category=db_inv.category,
        risk_category=db_inv.risk_category,
        initial_price=db_inv.initial_price,
        inv_type=db_inv.inv_type,
        transactions=txn_list,
        metrics=InvestmentMetrics(**metrics_data)
    )


def calculate_investment_metrics(investment: Investment) -> InvestmentMetrics:
    """Calculates key metrics (invested, value, return, CAGR) for a single investment."""
    # ... (Keep the existing metric calculation logic exactly the same, as it operates on the Pydantic model)
    #
    total_units = 0.0
    total_invested = 0.0

    txn_data = []

    for txn in investment.transactions:
        amount = txn.units * txn.price
        if txn.type_str == 'Buy':
            total_units += txn.units
            total_invested += amount
            txn_data.append({'date': txn.date_str, 'flow': -amount})
        elif txn.type_str == 'Sell':
            total_units -= txn.units
            if total_invested > 0 and total_units >= 0:
                cost_per_unit = total_invested / (total_units + txn.units)
                reduction = txn.units * cost_per_unit
                total_invested -= reduction

            txn_data.append({'date': txn.date_str, 'flow': amount})

    market_value = total_units * investment.initial_price

    absolute_return_amount = market_value - total_invested
    absolute_return_percent = (absolute_return_amount / total_invested) * 100 if total_invested > 0 else 0.0

    cagr = 0.0
    if txn_data:
        if market_value > 0 and total_invested > 0:

            # Simple annualized return approximation
            first_buy_date = min([t.date_str for t in investment.transactions if t.type_str == 'Buy'])
            time_in_years = (datetime.now().date() - first_buy_date).days / 365.25

            if time_in_years > 0:
                cagr = ((market_value / total_invested) ** (1 / time_in_years) - 1) * 100
            else:
                cagr = 0.0  # Same day investment

    return InvestmentMetrics(
        total_units=max(0.0, total_units),
        total_invested=max(0.0, total_invested),
        market_value=max(0.0, market_value),
        absolute_return_percent=absolute_return_percent,
        cagr=cagr
    )


# --- CRUD Operations (Updated to use SQLite/SQLAlchemy) ---

def get_all_investments_with_metrics(session: Session = next(get_db_session())) -> Dict[str, Investment]:
    """Retrieves all investments and recalculates metrics."""
    investments_dict = {}

    # Load investments and their transactions in one query (eager loading)
    db_investments = session.query(DBInvestment).options(joinedload(DBInvestment.transactions)).all()

    for db_inv in db_investments:
        inv = map_db_to_pydantic_investment(db_inv)
        inv.metrics = calculate_investment_metrics(inv)

        # Update the DB document with the latest metrics
        db_inv.metrics = inv.metrics.model_dump()
        session.add(db_inv)

        investments_dict[inv.name] = inv

    session.commit()
    return investments_dict


def get_portfolio_summary(investments: Dict[str, Investment]) -> Dict[str, Any]:
    """Calculates overall portfolio summary metrics."""
    # ... (Keep this function the same as it operates on the Pydantic models)
    total_invested_capital = sum(inv.metrics.total_invested for inv in investments.values())
    total_market_value = sum(inv.metrics.market_value for inv in investments.values())

    overall_absolute_return_percent = (
        ((total_market_value - total_invested_capital) / total_invested_capital) * 100
        if total_invested_capital > 0 else 0.0
    )

    return {
        "total_invested_capital": total_invested_capital,
        "total_market_value": total_market_value,
        "overall_absolute_return_percent": overall_absolute_return_percent,
        "last_calculated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def add_new_investment_asset(data: Investment, session: Session = next(get_db_session())) -> Investment:
    """Adds a new investment asset definition to the database."""
    if session.query(DBInvestment).filter(DBInvestment.name == data.name).first():
        raise ValueError("Investment with this name already exists.")

    new_db_inv = DBInvestment(
        name=data.name,
        category=data.category,
        risk_category=data.risk_category,
        initial_price=data.initial_price,
        inv_type=data.inv_type,
        metrics=calculate_investment_metrics(data).model_dump()
    )

    session.add(new_db_inv)
    session.commit()
    session.refresh(new_db_inv)

    return map_db_to_pydantic_investment(new_db_inv)


def add_transaction_to_investment(inv_name: str, txn_data: Transaction, session: Session = next(get_db_session())) -> Investment:
    """Adds a transaction to an existing investment."""
    db_inv = session.query(DBInvestment).filter(DBInvestment.name == inv_name).options(joinedload(DBInvestment.transactions)).first()

    if not db_inv:
        raise ValueError(f"Investment '{inv_name}' not found.")

    # Create new DBTransaction object
    new_db_txn = DBTransaction(
        date_str=txn_data.date_str,
        type_str=txn_data.type_str,
        units=txn_data.units,
        price=txn_data.price,
        utc=txn_data.utc,
        investment_id=db_inv.id
    )

    # Add to the session and commit
    session.add(new_db_txn)
    session.commit()

    # Refresh to get the latest transactions list (now including the new one)
    session.refresh(db_inv)

    # Recalculate metrics on the Pydantic model
    investment = map_db_to_pydantic_investment(db_inv)
    investment.metrics = calculate_investment_metrics(investment)

    # Update the metrics back in the DB
    db_inv.metrics = investment.metrics.model_dump()
    session.add(db_inv)
    session.commit()

    return investment