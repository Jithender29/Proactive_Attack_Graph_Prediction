from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..db import Category, Product
from ..middleware import get_db
from ..templates_config import render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.name).all()
    featured = db.query(Product).limit(12).all()
    return render_template(
        "home.html",
        request=request,
        context={"categories": categories, "featured": featured, "selected_category": None},
        db=db,
    )
