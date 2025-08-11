from fastapi import FastAPI
from .db import init_db
from .api.routes import merchants, transactions, webhooks, onboarding
from . import admin as admin_ui

app = FastAPI(title="TapSnap API", version="0.1.0")
init_db()

@app.get("/healthz")
def healthz():
    return {"ok": True}

app.include_router(merchants.router)
app.include_router(transactions.router)
app.include_router(webhooks.router)
app.include_router(onboarding.router)
app.include_router(admin_ui.router)
