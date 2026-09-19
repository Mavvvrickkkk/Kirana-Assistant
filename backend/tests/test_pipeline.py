import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from pipeline.voice_pipeline import VoicePipeline
from models import Product, ProductAlias, InventoryMovement
from schemas import TransactionCreate

# Isolated in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Setup initial data
    p1 = Product(name="Rice", name_local="బియ్యం", category="Grains", base_unit="kg", current_stock=100.0, reorder_level=10.0, selling_price=50.0)
    p2 = Product(name="Sugar", category="Groceries", base_unit="kg", current_stock=3.0, reorder_level=5.0, selling_price=40.0)
    p3 = Product(name="Green Gram", category="Pulses", base_unit="kg", current_stock=10.0, reorder_level=5.0, selling_price=80.0)
    p4 = Product(name="Moong Dal", category="Pulses", base_unit="kg", current_stock=10.0, reorder_level=5.0, selling_price=90.0)
    
    session.add_all([p1, p2, p3, p4])
    session.commit()
    
    a1 = ProductAlias(product_id=p1.id, alias="biyyam", language="te", source="seed")
    a2 = ProductAlias(product_id=p1.id, alias="chawal", language="hi", source="seed")
    session.add_all([a1, a2])
    session.commit()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_add_stock_english(db):
    os.environ["USE_MOCK_AI"] = "true"
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="Add 20 kg rice")
    assert proposal.intent == "ADD_STOCK"
    assert len(proposal.resolved_lines) == 1
    assert proposal.resolved_lines[0].product_name == "Rice"
    assert proposal.resolved_lines[0].quantity == 20.0

def test_multilingual_te_english_biyyam(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="biyyam 5 kilo add cheyyi")
    assert proposal.intent == "ADD_STOCK"
    assert proposal.resolved_lines[0].product_name == "Rice"
    assert proposal.resolved_lines[0].quantity == 5.0

def test_multilingual_hi_chawal(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="chawal 5 kg add karo")
    assert proposal.intent == "ADD_STOCK"
    assert proposal.resolved_lines[0].product_name == "Rice"

def test_fuzzy_matching_typo(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="Add 10 kg rise")
    assert proposal.intent == "ADD_STOCK"
    assert proposal.resolved_lines[0].product_name == "Rice"

def test_ambiguous_green_dal(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="Add 10 green dal")
    assert proposal.needs_clarification is True
    assert "Which product do you mean" in proposal.clarification_question

def test_check_stock_real_db(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="How much rice is left?")
    assert proposal.intent == "CHECK_STOCK"
    assert proposal.stock_query_result["current_stock"] == 100.0

def test_low_stock_real_db(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="Which products are running low?")
    assert proposal.intent == "LOW_STOCK"
    assert "Sugar" in proposal.stock_query_result["low_stock_products"]

def test_insufficient_stock_rejection(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="Sold 500 kg rice")
    assert proposal.needs_clarification is True
    assert "Insufficient stock" in proposal.clarification_question

def test_sales_summary(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="What sold most today?")
    assert proposal.intent == "SALES_SUMMARY"
    assert proposal.analytics_result is not None
    assert proposal.analytics_result["period"] == "today"

def test_check_stock_no_product(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="How much is left?")
    assert proposal.intent == "CHECK_STOCK"
    assert proposal.needs_clarification is True
    assert "Which product would you like to check?" in proposal.clarification_question

def test_multi_item_add(db):
    pipeline = VoicePipeline()
    proposal = pipeline.process_command(db, text="Add 5 kg rice and 2 kg sugar")
    assert proposal.intent == "ADD_STOCK"
    assert len(proposal.resolved_lines) == 2
    names = [l.product_name for l in proposal.resolved_lines]
    assert "Rice" in names
    assert "Sugar" in names