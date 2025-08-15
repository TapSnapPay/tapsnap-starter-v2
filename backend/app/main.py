from fastapi import FastAPI, Request
from .db import init_db
from .api.routes import merchants, transactions, webhooks, onboarding
from . import admin as admin_ui
from .public import router as public_router
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging


app = FastAPI(title="TapSnap API", version="0.1.0")
init_db()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

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

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
# If it's a 401, include the Basic-Auth challenge so the browser shows the login box
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

    # Pretty 404 page
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "path": request.url.path},
            status_code=404,
        )
    # Other HTTP errors (e.g., 401/403/405)
    return templates.TemplateResponse(
        "errors/error.html",
        {"request": request, "status_code": exc.status_code, "detail": getattr(exc, "detail", "")},
        status_code=exc.status_code,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # This catches things like missing required query/body fields (422)
    return templates.TemplateResponse(
        "errors/error.html",
        {"request": request, "status_code": 422, "detail": "Invalid or missing input."},
        status_code=422,
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Catch-all for unexpected errors (500)
    logging.exception("Unhandled error: %s", exc)
    return templates.TemplateResponse(
        "errors/error.html",
        {"request": request, "status_code": 500, "detail": "Something went wrong on our side."},
        status_code=500,
    )
