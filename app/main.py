from fastapi import FastAPI
from app.routers import portfolio, transactions, sips
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="iWealthBuilder API",
    description="Backend for managing investment portfolios and SIPs.",
    version="1.0.0"
)

# CORS Middleware setup to allow communication from Streamlit (running on a different port)
origins = [
    "http://localhost",
    "http://localhost:8501",  # Default Streamlit port
    "http://127.0.0.1:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database data

# Include routers
app.include_router(portfolio.router)
app.include_router(transactions.router)
app.include_router(sips.router) # NEW SIP Router

@app.get("/")
def read_root():
    return {"message": "iWealthBuilder API is running."}

# To run the API: uvicorn app.main:app --reload