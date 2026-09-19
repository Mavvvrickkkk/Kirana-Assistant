from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models import Product
from schemas import (
    ProductSchema,
    SyncItemResult,
    SyncRequest,
    TransactionCreate,
)
from services.inventory_service import InventoryService
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=list[ProductSchema])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.is_active == True).all()


@router.get("/low-stock", response_model=list[ProductSchema])
def get_low_stock(db: Session = Depends(get_db)):
    return (
        db.query(Product)
        .filter(
            Product.is_active == True, Product.current_stock <= Product.reorder_level
        )
        .all()
    )


@router.post("/transaction")
def execute_manual_tx(tx: TransactionCreate, db: Session = Depends(get_db)):
    try:
        movement = InventoryService.commit_transaction(db, tx, source="MANUAL")
        return {
            "status": "SUCCESS",
            "stock_after": movement.stock_after,
            "movement_id": movement.id,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync/transactions", response_model=list[SyncItemResult])
def sync_offline_queue(req: SyncRequest, db: Session = Depends(get_db)):
    results = []
    for tx in req.transactions:
        try:
            m = InventoryService.commit_transaction(db, tx, source="OFFLINE_SYNC")
            results.append(
                SyncItemResult(client_txn_id=tx.client_txn_id, status="SUCCESS")
            )
        except Exception as e:
            results.append(
                SyncItemResult(
                    client_txn_id=tx.client_txn_id,
                    status="ERROR",
                    error=str(e),
                )
            )
    return results