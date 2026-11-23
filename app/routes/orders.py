from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import Order, User
from ..middleware import get_db
from ..templates_config import render_template

router = APIRouter()


@router.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=302)

    orders = db.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    return render_template(
        "orders.html",
        request=request,
        context={"orders": orders},
        db=db,
    )


@router.get("/api/orders/{order_id}")
def api_order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != user_id:
        # Check if user is admin
        user = db.query(User).filter_by(id=user_id).first()
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Forbidden")

    return {
        "id": order.id,
        "total": order.total,
        "created_at": str(order.created_at),
        "items": [
            {
                "product_id": item.product_id,
                "title": item.product.title if item.product else f"Product #{item.product_id}",
                "quantity": item.quantity,
                "price": item.price,
            }
            for item in order.items
        ],
    }
