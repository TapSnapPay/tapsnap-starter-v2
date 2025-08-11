from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import models

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db)):
    merchants = db.query(models.Merchant).order_by(models.Merchant.id.desc()).all()
    txs = db.query(models.Transaction).order_by(models.Transaction.id.desc()).limit(50).all()
    return templates.TemplateResponse("admin/index.html", {"request": request, "merchants": merchants, "txs": txs})

@router.post("/merchants/new", response_class=HTMLResponse)
async def create_merchant(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = form.get("name", "").strip()
    email = form.get("email", "").strip()
    if name and email:
        m = models.Merchant(name=name, email=email)
        db.add(m)
        db.commit()
    return RedirectResponse(url="/admin/", status_code=303)
