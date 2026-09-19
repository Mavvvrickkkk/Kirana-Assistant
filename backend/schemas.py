from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProductItemExtraction(BaseModel):
    product_mention: str
    quantity: Optional[float] = None
    unit: Optional[str] = None


class LLMExtractedIntent(BaseModel):
    language: str = "en"
    intent: str  # ADD_STOCK, REMOVE_STOCK, CHECK_STOCK, LOW_STOCK, SALES_SUMMARY, UNKNOWN
    items: List[ProductItemExtraction] = []
    time_range: Optional[str] = None


class ResolvedLineItem(BaseModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_mention: str
    quantity: float
    unit: str
    confidence: float
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


class VoiceCommandProposal(BaseModel):
    command_id: str
    status: str
    transcript: str
    intent: str
    language: str
    resolved_lines: List[ResolvedLineItem] = []
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    stock_query_result: Optional[Dict[str, Any]] = None
    analytics_result: Optional[Dict[str, Any]] = None


class TransactionCreate(BaseModel):
    client_txn_id: Optional[str] = None
    product_id: int
    type: str  # ADD_STOCK / REMOVE_STOCK
    quantity: float
    unit: str


class SyncRequest(BaseModel):
    transactions: List[TransactionCreate]


class SyncItemResult(BaseModel):
    client_txn_id: Optional[str]
    status: str  # SUCCESS, DUPLICATE, ERROR
    error: Optional[str] = None


class ProductSchema(BaseModel):
    id: int
    name: str
    name_local: Optional[str]
    category: str
    base_unit: str
    current_stock: float
    reorder_level: float
    selling_price: float
    is_active: bool

    class Config:
        from_attributes = True


class MovementSchema(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    movement_type: str
    quantity_delta: float
    stock_after: float
    unit_price: Optional[float] = None
    command_id: Optional[str] = None
    client_txn_id: Optional[str] = None
    occurred_at: datetime

    class Config:
        from_attributes = True