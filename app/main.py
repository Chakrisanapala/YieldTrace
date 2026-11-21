"""
FastAPI application entry point for YieldTrace.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.modules.inventory.router import router as inventory_router
from app.modules.purchases.router import router as purchases_router
from app.modules.production.router import router as production_router

app = FastAPI(
    title="YieldTrace Production Engine",
    description="Precision Yield Tracking, Inventory Ledger, and Variance Forensics API",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include module routers
app.include_router(inventory_router)
app.include_router(purchases_router)
app.include_router(production_router)


@app.on_event("startup")
def on_startup():
    """Initialize database tables on application start."""
    init_db()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "YieldTrace",
        "version": "0.1.0"
    }


@app.get("/")
def root():
    return {
        "message": "Welcome to YieldTrace Production & Variance Accounting Engine",
        "docs": "/docs",
        "health": "/api/health"
    }
