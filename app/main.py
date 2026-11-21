"""
FastAPI application entry point for YieldTrace.
Intelligent Production, Variance Forensics, and Audit Intelligence Platform.
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.database import init_db
from app.modules.auth.router import router as auth_router
from app.modules.master.router import router as master_router
from app.modules.inventory.router import router as inventory_router
from app.modules.purchases.router import router as purchases_router
from app.modules.production.router import router as production_router
from app.modules.sales.router import router as sales_router
from app.modules.insight.router import router as insight_router
from app.modules.reports.router import router as reports_router
from app.modules.dashboard.router import router as dashboard_router

app = FastAPI(
    title="YieldTrace — Production Variance Forensics & Audit Platform",
    description="Intelligent Production, Variance Forensics and Audit Intelligence Platform for Food Manufacturers",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files and Templates
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir)

# Include Module Routers
app.include_router(auth_router)
app.include_router(master_router)
app.include_router(inventory_router)
app.include_router(purchases_router)
app.include_router(production_router)
app.include_router(sales_router)
app.include_router(insight_router)
app.include_router(reports_router)
app.include_router(dashboard_router)


@app.on_event("startup")
def on_startup():
    """Ensure database schema is created on startup."""
    init_db()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "YieldTrace",
        "version": "1.0.0",
        "tagline": "Every gram accounted for. Every deviation explained."
    }


@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    """Serve the single-page application / UI shell."""
    return templates.TemplateResponse(request=request, name="index.html")
