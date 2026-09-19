from datetime import datetime
from database import Base
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    name_local = Column(String(100), nullable=True)
    category = Column(String(50), default="General")
    base_unit = Column(String(20), nullable=False, default="kg")
    current_stock = Column(Float, nullable=False, default=0.0)
    reorder_level = Column(Float, nullable=False, default=5.0)
    selling_price = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    alias = Column(String(100), nullable=False, index=True)
    language = Column(String(10), default="te")
    source = Column(String(20), default="user_confirmed")  # seed, llm, user_confirmed
    usage_count = Column(Integer, default=1)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String(20), nullable=False)  # PURCHASE_IN, SALE_OUT, ADJUSTMENT
    quantity_delta = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=True)
    stock_after = Column(Float, nullable=False)
    command_id = Column(String(36), nullable=True)
    client_txn_id = Column(String(64), nullable=True, unique=True, index=True)
    needs_recount = Column(Boolean, default=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VoiceCommand(Base):
    __tablename__ = "voice_commands"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    status = Column(String(30), nullable=False, default="PENDING_CONFIRMATION")  # PENDING_CONFIRMATION, CONFIRMED, CANCELLED, REJECTED, EXECUTED
    transcript = Column(Text, nullable=False)
    intent = Column(String(30), nullable=False)
    proposal_json = Column(Text, nullable=False)
    clarification_question = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())