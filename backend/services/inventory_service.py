from sqlalchemy.orm import Session
from models import InventoryMovement, Product
from schemas import TransactionCreate
from services.validator import validate_and_convert_unit

class InventoryService:

    @staticmethod
    def commit_proposal_atomic(
        db: Session, proposal_lines: list, intent: str, command_id: str = None
    ) -> list:
        movements = []
        try:
            for line in proposal_lines:
                # Handle both dict (from API JSON payload) and object access
                product_id = line["product_id"] if isinstance(line, dict) else line.product_id
                quantity = line["quantity"] if isinstance(line, dict) else line.quantity
                unit = line["unit"] if isinstance(line, dict) else line.unit
                
                product = (
                    db.query(Product)
                    .filter(Product.id == product_id, Product.is_active == True)
                    .with_for_update()
                    .first()
                )
                if not product:
                    raise ValueError(f"Product ID {product_id} not found.")

                valid_unit, converted_qty, err = validate_and_convert_unit(unit, product.base_unit, quantity)
                if not valid_unit:
                    raise ValueError(err)

                delta = converted_qty if intent == "ADD_STOCK" else -converted_qty
                if intent == "REMOVE_STOCK" and product.current_stock < converted_qty:
                    raise ValueError(
                        f"Insufficient stock for {product.name}. Available: {product.current_stock} {product.base_unit}, Requested: {converted_qty} {product.base_unit}"
                    )

                product.current_stock += delta
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type="PURCHASE_IN" if intent == "ADD_STOCK" else "SALE_OUT",
                    quantity_delta=delta,
                    unit_price=product.selling_price,
                    stock_after=product.current_stock,
                    command_id=command_id,
                )
                db.add(movement)
                movements.append(movement)
                
            db.commit()
            return movements
        except Exception as e:
            db.rollback()
            raise ValueError(f"Atomic transaction rolled back: {str(e)}")

    @staticmethod
    def commit_transaction(
        db: Session,
        tx: TransactionCreate,
        command_id: str = None,
        source: str = "VOICE",
    ) -> InventoryMovement:
        if tx.client_txn_id:
            existing = db.query(InventoryMovement).filter(InventoryMovement.client_txn_id == tx.client_txn_id).first()
            if existing:
                return existing

        if tx.quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        product = db.query(Product).filter(Product.id == tx.product_id, Product.is_active == True).first()
        if not product:
            raise ValueError(f"Product ID {tx.product_id} not found.")

        valid_unit, converted_qty, err = validate_and_convert_unit(tx.unit, product.base_unit, tx.quantity)
        if not valid_unit:
            raise ValueError(err)

        m_type = "PURCHASE_IN" if tx.type == "ADD_STOCK" else "SALE_OUT"
        delta = converted_qty if tx.type == "ADD_STOCK" else -converted_qty

        if tx.type == "REMOVE_STOCK" and product.current_stock < converted_qty:
            raise ValueError(
                f"Insufficient stock for {product.name}. Current: {product.current_stock} {product.base_unit}, Requested: {converted_qty} {product.base_unit}"
            )

        product.current_stock += delta

        movement = InventoryMovement(
            product_id=product.id,
            movement_type=m_type,
            quantity_delta=delta,
            unit_price=product.selling_price,
            stock_after=product.current_stock,
            command_id=command_id,
            client_txn_id=tx.client_txn_id,
        )

        db.add(movement)
        db.commit()
        db.refresh(movement)
        db.refresh(product)
        return movement