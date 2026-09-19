from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from database import get_db
from fastapi import APIRouter, Depends, Query
from models import InventoryMovement, Product
from schemas import MovementSchema
from sqlalchemy import func
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/sales-summary")
def get_sales_summary(
    period: str = Query("today", regex="^(today|week|month)$"),
    db: Session = Depends(get_db),
):
    tz = ZoneInfo("Asia/Kolkata")
    now_local = datetime.now(tz)

    if period == "today":
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_local = now_local - timedelta(days=7)
    else:
        start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    start_utc = start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    sales = (
        db.query(InventoryMovement)
        .filter(
            InventoryMovement.movement_type == "SALE_OUT",
            InventoryMovement.occurred_at >= start_utc,
        )
        .all()
    )

    total_units = sum([abs(m.quantity_delta) for m in sales])
    revenue = sum([abs(m.quantity_delta) * (m.unit_price or 0.0) for m in sales])

    top_products_query = (
        db.query(
            Product.name,
            func.sum(func.abs(InventoryMovement.quantity_delta)).label("total_qty"),
        )
        .join(Product, Product.id == InventoryMovement.product_id)
        .filter(
            InventoryMovement.movement_type == "SALE_OUT",
            InventoryMovement.occurred_at >= start_utc,
        )
        .group_by(Product.name)
        .order_by(func.sum(func.abs(InventoryMovement.quantity_delta)).desc())
        .limit(5)
        .all()
    )

    top_products = [{"name": name, "quantity": qty} for name, qty in top_products_query]

    return {
        "period": period,
        "total_units_sold": total_units,
        "total_revenue": revenue,
        "top_selling_products": top_products,
    }

@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    movements = (
        db.query(InventoryMovement)
        .order_by(InventoryMovement.occurred_at.desc())
        .limit(50)
        .all()
    )
    # Enrich with product names
    results = []
    for m in movements:
        product = db.query(Product).filter(Product.id == m.product_id).first()
        results.append(
            MovementSchema(
                id=m.id,
                product_id=m.product_id,
                product_name=product.name if product else "Unknown",
                movement_type=m.movement_type,
                quantity_delta=m.quantity_delta,
                stock_after=m.stock_after,
                unit_price=m.unit_price,
                command_id=m.command_id,
                client_txn_id=m.client_txn_id,
                occurred_at=m.occurred_at,
            )
        )
    return results