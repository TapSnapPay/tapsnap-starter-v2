# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from pathlib import Path
import logging

# app internals
from .db import init_db
from .api.routes import merchants, transactions, webhooks, onboarding
from .admin import admin_ui                  # import the APIRouter instance from admin.py
from .public import router as public_router  # your file is public.py


app = FastAPI(title="TapSnap API", version="0.1.0")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "https://tapsnap.app",     # <- change to your real frontend domain later
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create tables on startup if needed
init_db()

# templates for error pages
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

@app.get("/health")
def health():
    return {"ok": True}

# One root route → redirect to admin UI
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/admin", status_code=307)

# Mount feature routers
app.include_router(merchants.router)
app.include_router(transactions.router)
app.include_router(webhooks.router)
app.include_router(onboarding.router)

app.include_router(admin_ui)         # ✅ admin: do NOT use .router here
app.include_router(public_router)    # ✅ public: do NOT use .router here

# -----------------------------
# Nicely formatted error pages
# -----------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # 401: show “Unauthorized” page and trigger Basic Auth box
    if exc.status_code == 401:
        return templates.TemplateResponse(
            "errors/error.html",
            {
                "request": request,
                "status_code": 401,
                "detail": "Unauthorized",
            },
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
        )

    # 404: friendly “Not Found”
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "path": request.url.path},
            status_code=404,
        )

    # Everything else (403/405/etc.)
    return templates.TemplateResponse(
        "errors/error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "detail": getattr(exc, "detail", ""),
        },
        status_code=exc.status_code,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 422: invalid or missing input
    return templates.TemplateResponse(
        "errors/error.html",
        {
            "request": request,
            "status_code": 422,
            "detail": "Invalid or missing input.",
        },
        status_code=422,
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # 500: anything unexpected
    logging.exception("Unhandled error: %s", exc)
    return templates.TemplateResponse(
        "errors/error.html",
        {
            "request": request,
            "status_code": 500,
            "detail": "Something went wrong on our side.",
        },
        status_code=500,
    )

