"""
Master Data API Endpoints for YieldTrace.
Covers:
- Products & Items Master
- Customers Master
- Suppliers Master
- Unit Conversions
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Item, ItemCategory, Customer, Supplier, UnitConversion

router = APIRouter(prefix="/api/master", tags=["Master Data"])


# ---------------------------------------------
# Products / Items
# ---------------------------------------------
class ItemCreateRequest(BaseModel):
    code: str
    name: str
    category: ItemCategory
    unit: str
    standard_cost: float = Field(ge=0)
    selling_price: float = Field(ge=0, default=0.0)
    gst_rate: float = Field(ge=0, default=5.0)
    reorder_level: float = Field(ge=0, default=0.0)
    description: Optional[str] = None


@router.get("/items")
def list_items(category: Optional[ItemCategory] = None, db: Session = Depends(get_db)):
    """List all active items in master catalog."""
    query = db.query(Item).filter(Item.is_active == True)
    if category:
        query = query.filter(Item.category == category)
    items = query.order_by(Item.code.asc()).all()
    return [
        {
            "id": i.id,
            "code": i.code,
            "name": i.name,
            "category": i.category.value,
            "unit": i.unit,
            "standard_cost": i.standard_cost,
            "current_wauc": i.current_wauc,
            "selling_price": i.selling_price,
            "gst_rate": i.gst_rate,
            "reorder_level": i.reorder_level,
            "description": i.description
        }
        for i in items
    ]


@router.post("/items")
def create_item(payload: ItemCreateRequest, db: Session = Depends(get_db)):
    """Create a new item in master catalog."""
    existing = db.query(Item).filter(Item.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Item code '{payload.code}' already exists.")

    item = Item(
        code=payload.code,
        name=payload.name,
        category=payload.category,
        unit=payload.unit,
        standard_cost=payload.standard_cost,
        current_wauc=payload.standard_cost,  # Initial WAUC matches standard cost
        selling_price=payload.selling_price,
        gst_rate=payload.gst_rate,
        reorder_level=payload.reorder_level,
        description=payload.description,
        is_active=True
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "code": item.code, "name": item.name, "message": "Item created successfully"}


# ---------------------------------------------
# Customers
# ---------------------------------------------
class CustomerCreateRequest(BaseModel):
    code: str
    name: str
    customer_type: str = "retailer"
    gstin: Optional[str] = None
    state: str = "Tamil Nadu"
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None


@router.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    """List all registered customers."""
    customers = db.query(Customer).order_by(Customer.name.asc()).all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "customer_type": c.customer_type,
            "gstin": c.gstin,
            "state": c.state,
            "contact_phone": c.contact_phone,
            "contact_email": c.contact_email,
            "address": c.address
        }
        for c in customers
    ]


@router.post("/customers")
def create_customer(payload: CustomerCreateRequest, db: Session = Depends(get_db)):
    """Create a new customer profile."""
    existing = db.query(Customer).filter(Customer.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Customer code '{payload.code}' already exists.")

    c = Customer(
        code=payload.code,
        name=payload.name,
        customer_type=payload.customer_type,
        gstin=payload.gstin,
        state=payload.state,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        address=payload.address
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "code": c.code, "name": c.name, "message": "Customer created successfully"}


# ---------------------------------------------
# Suppliers
# ---------------------------------------------
class SupplierCreateRequest(BaseModel):
    code: str
    name: str
    gstin: Optional[str] = None
    state: str = "Tamil Nadu"
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None


@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    """List all registered suppliers."""
    suppliers = db.query(Supplier).order_by(Supplier.name.asc()).all()
    return [
        {
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "gstin": s.gstin,
            "state": s.state,
            "contact_phone": s.contact_phone,
            "contact_email": s.contact_email,
            "address": s.address
        }
        for s in suppliers
    ]


@router.post("/suppliers")
def create_supplier(payload: SupplierCreateRequest, db: Session = Depends(get_db)):
    """Create a new supplier profile."""
    existing = db.query(Supplier).filter(Supplier.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Supplier code '{payload.code}' already exists.")

    s = Supplier(
        code=payload.code,
        name=payload.name,
        gstin=payload.gstin,
        state=payload.state,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        address=payload.address
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "code": s.code, "name": s.name, "message": "Supplier created successfully"}
