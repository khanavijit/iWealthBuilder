import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, JSON, ForeignKey, event, DDL
from sqlalchemy.orm import declarative_base, Session, relationship
from datetime import datetime
import json
import os

# --- Configuration ---
# Use an absolute path for the SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'investment_portfolio.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- SQLAlchemy Setup ---
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite with FastAPI
)
Base = declarative_base()


# --- Database Models ---

class DBInvestment(Base):
    """SQLAlchemy model for an Investment asset."""
    __tablename__ = 'investments'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String)
    risk_category = Column(String)
    initial_price = Column(Float, default=100.0)
    inv_type = Column(String, default="Flexible")

    # Relationships
    transactions = relationship("DBTransaction", back_populates="investment", cascade="all, delete-orphan")
    sips = relationship("DBSIPDefinition", back_populates="investment", cascade="all, delete-orphan")

    # Store metrics as JSON (or break it out into a separate table if complex)
    # Using JSON for simplicity, though a proper relational design might use columns
    metrics = Column(JSON, default={})

    def __repr__(self):
        return f"<Investment(name='{self.name}', category='{self.category}')>"


class DBTransaction(Base):
    """SQLAlchemy model for a Transaction."""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey('investments.id'))

    date_str = Column(Date)
    type_str = Column(String)  # 'Buy' or 'Sell'
    units = Column(Float)
    price = Column(Float)
    utc = Column(Float, default=0.0)

    # Relationships
    investment = relationship("DBInvestment", back_populates="transactions")


class DBSIPDefinition(Base):
    """SQLAlchemy model for a SIP Definition (Schedule)."""
    __tablename__ = 'sips'

    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey('investments.id'))
    investment_name = Column(String, index=True)  # Redundant but useful for queries

    amount = Column(Float)
    frequency = Column(String)  # 'Monthly', 'Weekly', etc.
    start_date = Column(Date)
    status = Column(String, default="Active")

    # Relationships
    investment = relationship("DBInvestment", back_populates="sips")

    def __repr__(self):
        return f"<SIP(inv='{self.investment_name}', freq='{self.frequency}', amount='{self.amount}')>"


# --- Initialization Functions ---

def create_db_and_tables():
    """Create the database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Dependency injector for database sessions."""
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


def initialize_data_sqlite(session: Session):
    """Initializes the SQLite database with starting data if tables are empty."""
    if session.query(DBInvestment).count() == 0:
        print("Initializing SQLite database with sample data...")

        # 1. Global Tech Fund
        tech_inv = DBInvestment(
            name="Global Tech Fund",
            category="Equity",
            risk_category="High",
            initial_price=150.0,
            inv_type="MF"
        )
        tech_inv.transactions.extend([
            DBTransaction(date_str=datetime(2023, 1, 1).date(), type_str="Buy", units=100.0, price=100.0),
            DBTransaction(date_str=datetime(2023, 2, 1).date(), type_str="Buy", units=10.0, price=110.0),
        ])
        tech_inv.sips.extend([
            DBSIPDefinition(investment_name="Global Tech Fund", amount=1500.0, frequency="Monthly", start_date=datetime(2023, 3, 15).date())
        ])

        # 2. Government Bonds ETF
        bonds_inv = DBInvestment(
            name="Government Bonds ETF",
            category="Bonds",
            risk_category="Low",
            initial_price=95.0,
            inv_type="ETF"
        )
        bonds_inv.transactions.extend([
            DBTransaction(date_str=datetime(2022, 10, 1).date(), type_str="Buy", units=500.0, price=90.0)
        ])

        session.add_all([tech_inv, bonds_inv])
        session.commit()
        print("Initialization complete.")


# Create tables and initialize data on startup
create_db_and_tables()
with Session(bind=engine) as session:
    initialize_data_sqlite(session)