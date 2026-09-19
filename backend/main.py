from database import Base, SessionLocal, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import Product, ProductAlias
from routers import analytics, inventory, voice

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Multilingual Kirana Voice Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(analytics.router, prefix="/api/reports", tags=["Analytics"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Kirana Voice API"}


def seed_database():
    db = SessionLocal()
    if db.query(Product).count() == 0:
        p1 = Product(
            name="Rice",
            name_local="బియ్యం",
            category="Grains",
            base_unit="kg",
            current_stock=100.0,
            reorder_level=10.0,
            selling_price=50.0,
        )
        p2 = Product(
            name="Basmati Rice",
            name_local="బాస్మతి బియ్యం",
            category="Grains",
            base_unit="kg",
            current_stock=25.0,
            reorder_level=5.0,
            selling_price=120.0,
        )
        p3 = Product(
            name="Moong Dal",
            name_local="పెసర పప్పు",
            category="Pulses",
            base_unit="kg",
            current_stock=15.0,
            reorder_level=5.0,
            selling_price=90.0,
        )
        p4 = Product(
            name="Sugar",
            name_local="చక్కెర",
            category="Groceries",
            base_unit="kg",
            current_stock=3.0,
            reorder_level=5.0,
            selling_price=40.0,
        )
        p5 = Product(
            name="Green Gram",
            name_local="పెసలు",
            category="Pulses",
            base_unit="kg",
            current_stock=8.0,
            reorder_level=3.0,
            selling_price=85.0,
        )

        db.add_all([p1, p2, p3, p4, p5])
        db.commit()

        a1 = ProductAlias(
            product_id=p1.id, alias="biyyam", language="te", source="seed"
        )
        a2 = ProductAlias(
            product_id=p1.id, alias="chawal", language="hi", source="seed"
        )
        a3 = ProductAlias(
            product_id=p4.id, alias="chakkera", language="te", source="seed"
        )
        db.add_all([a1, a2, a3])
        db.commit()
    db.close()


@app.on_event("startup")
def on_startup():
    seed_database()