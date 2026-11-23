from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..db import Product, User
from ..middleware import get_db
from ..templates_config import render_template

router = APIRouter()


def _require_admin(request: Request, db: Session) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.query(User).filter_by(id=user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request, db)
    products = db.query(Product).all()
    return render_template(
        "admin.html",
        request=request,
        context={"products": products, "user": admin_user},
        db=db,
    )


@router.get("/api/admin/inventory")
def api_inventory(request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    products = db.query(Product).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "price": p.price,
            "stock": p.stock,
            "category": p.category.name if p.category else "Unassigned",
        }
        for p in products
    ]
