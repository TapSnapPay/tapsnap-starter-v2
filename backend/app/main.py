from fastapi import FastAPI
from .db import init_db
from .api.routes import merchants, transactions, webhooks, onboarding
from . import admin as admin_ui
from .public import router as public_router
from fastapi.responses import RedirectResponse


app = FastAPI(title="TapSnap API", version="0.1.0")
init_db()

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/admin", status_code=307)


app.include_router(merchants.router)
app.include_router(transactions.router)
app.include_router(webhooks.router)
app.include_router(onboarding.router)
app.include_router(admin_ui.router)
app.include_router(public_router)

@app.get("/", include_in_schema=False)
def root():
    # send anyone who visits the root to the admin UI
    return RedirectResponse(url="/admin", status_code=307)
