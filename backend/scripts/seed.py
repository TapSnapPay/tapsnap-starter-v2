from app.db import SessionLocal, init_db
from app import models

init_db()
db = SessionLocal()

if db.query(models.Merchant).count() == 0:
    demo = models.Merchant(name="Demo Shop", email="demo@shop.local")
    db.add(demo)
    db.commit()
    print("Seeded Demo Shop (id=", demo.id, ")")
else:
    print("Merchants already exist, skipping.")
db.close()
