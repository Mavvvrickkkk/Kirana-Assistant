import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from models import InventoryMovement, Product, VoiceCommand
from schemas import ResolvedLineItem, VoiceCommandProposal
from services.nlu import NLUService
from services.normalizer import ProductNormalizer
from services.stt import STTService
from services.validator import normalize_unit, validate_operation
from sqlalchemy import func
from sqlalchemy.orm import Session


class VoicePipeline:

    def __init__(self):
        self.stt = STTService()
        self.nlu = NLUService()
        self.normalizer = ProductNormalizer()

    def process_command(
        self, db: Session, audio_bytes: bytes = None, text: str = None
    ) -> VoiceCommandProposal:
        transcript = self.stt.transcribe(
            audio_bytes=audio_bytes, text_override=text
        )
        extracted = self.nlu.parse_intent_and_entities(transcript)

        command_id = str(uuid.uuid4())
        resolved_lines = []
        needs_clarification = False
        clarification_question = None
        stock_query_result = None
        analytics_result = None

        # ── READ INTENTS (no confirmation needed) ──────────────────────
        if extracted.intent == "CHECK_STOCK":
            if not extracted.items:
                # C4 FIX: No product mentioned → ask for clarification instead of defaulting to "sugar"
                needs_clarification = True
                clarification_question = "Which product would you like to check?"
            else:
                mention = extracted.items[0].product_mention
                product, score, amb, q = self.normalizer.normalize(mention, db)

                if product:
                    stock_query_result = {
                        "product_id": product.id,
                        "product_name": product.name,
                        "current_stock": product.current_stock,
                        "unit": product.base_unit,
                        "message": f"You have {product.current_stock} {product.base_unit} of {product.name}.",
                    }
                else:
                    needs_clarification = True
                    clarification_question = q or "Product not found."

        elif extracted.intent == "LOW_STOCK":
            low_products = (
                db.query(Product)
                .filter(
                    Product.is_active == True,
                    Product.current_stock <= Product.reorder_level,
                )
                .all()
            )
            names = [p.name for p in low_products]
            msg = (
                f"Low stock items: {', '.join(names)}"
                if names
                else "All items have healthy stock levels."
            )
            stock_query_result = {"low_stock_products": names, "message": msg}

        # C5 FIX: Add SALES_SUMMARY handler
        elif extracted.intent == "SALES_SUMMARY":
            period = extracted.time_range or "today"
            tz = ZoneInfo("Asia/Kolkata")
            now_local = datetime.now(tz)

            if period == "today":
                start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start_local = now_local - timedelta(days=7)
            else:  # month
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

            total_units = sum(abs(m.quantity_delta) for m in sales)
            revenue = sum(abs(m.quantity_delta) * (m.unit_price or 0.0) for m in sales)

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

            if total_units == 0:
                msg = f"No sales recorded for {period}."
            else:
                top_str = ", ".join(f"{p['name']} ({p['quantity']})" for p in top_products[:3])
                msg = f"Sales for {period}: {total_units:.1f} units sold, ₹{revenue:.2f} revenue. Top products: {top_str}"

            analytics_result = {
                "period": period,
                "total_units_sold": total_units,
                "total_revenue": revenue,
                "top_selling_products": top_products,
                "message": msg,
            }

        # ── WRITE INTENTS (need confirmation) ──────────────────────────
        elif extracted.intent in ("ADD_STOCK", "REMOVE_STOCK"):
            for item in extracted.items:
                mention = item.product_mention or ""
                qty = item.quantity if item.quantity is not None else 1.0
                unit = normalize_unit(item.unit or "kg")

                product, conf, amb, amb_q = self.normalizer.normalize(mention, db)

                if amb or not product:
                    needs_clarification = True
                    clarification_question = amb_q
                    resolved_lines.append(
                        ResolvedLineItem(
                            product_mention=mention,
                            quantity=qty,
                            unit=unit,
                            confidence=conf,
                            needs_clarification=True,
                            clarification_question=amb_q,
                        )
                    )
                else:
                    # M1 FIX: Pass product.base_unit to validate_operation
                    valid, err = validate_operation(
                        extracted.intent, qty, unit, product.current_stock, product.base_unit
                    )
                    if not valid:
                        needs_clarification = True
                        clarification_question = err

                    resolved_lines.append(
                        ResolvedLineItem(
                            product_id=product.id,
                            product_name=product.name,
                            product_mention=mention,
                            quantity=qty,
                            unit=unit,
                            confidence=conf,
                            needs_clarification=not valid,
                            clarification_question=err if not valid else None,
                        )
                    )

        # ── UNKNOWN INTENT ─────────────────────────────────────────────
        else:
            needs_clarification = True
            clarification_question = (
                "Sorry, I didn't understand that command. "
                "Try saying something like 'Add 5 kg rice' or 'How much sugar is left?'"
            )

        # ── Determine correct status based on intent type ──────────────
        # C7 FIX: Only WRITE intents should be PENDING_CONFIRMATION
        is_write_intent = extracted.intent in ("ADD_STOCK", "REMOVE_STOCK")
        if is_write_intent and not needs_clarification:
            db_status = "PENDING_CONFIRMATION"
        elif is_write_intent and needs_clarification:
            db_status = "NEEDS_CLARIFICATION"
        else:
            # READ or UNKNOWN — no confirmation needed
            db_status = "COMPLETED"

        proposal = VoiceCommandProposal(
            command_id=command_id,
            status=db_status,
            transcript=transcript,
            intent=extracted.intent,
            language=extracted.language,
            resolved_lines=resolved_lines,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            stock_query_result=stock_query_result,
            analytics_result=analytics_result,
        )

        db_cmd = VoiceCommand(
            id=command_id,
            status=db_status,
            transcript=transcript,
            intent=extracted.intent,
            proposal_json=proposal.model_dump_json(),
            clarification_question=clarification_question,
        )
        db.add(db_cmd)
        db.commit()

        return proposal