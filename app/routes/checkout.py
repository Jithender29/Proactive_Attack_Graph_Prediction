from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import Product, Order, OrderItem, User
from ..middleware import get_db
from ..templates_config import render_template

router = APIRouter()


@router.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request, db: Session = Depends(get_db)):
    cart = request.session.get("cart", {})
    if not cart or not isinstance(cart, dict):
        return RedirectResponse("/cart", status_code=302)

    items = []
    subtotal = 0.0
    for pid, qty in cart.items():
        try:
            prod_id = int(pid)
        except (ValueError, TypeError):
            continue
        prod = db.query(Product).filter_by(id=prod_id).first()
        if not prod:
            continue
        line_total = prod.price * qty
        subtotal += line_total
        items.append({"product": prod, "qty": qty, "total": round(line_total, 2)})

    if not items:
        return RedirectResponse("/cart", status_code=302)

    return render_template(
        "checkout.html",
        request=request,
        context={"items": items, "subtotal": round(subtotal, 2)},
        db=db,
    )


@router.post("/api/checkout")
def api_checkout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required to complete checkout")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User account not found")

    cart = request.session.get("cart", {})
    if not cart or not isinstance(cart, dict):
        raise HTTPException(status_code=400, detail="Your cart is empty")

    total = 0.0
    order = Order(user_id=user.id, total=0.0)
    db.add(order)
    db.flush()

    for pid, qty in cart.items():
        try:
            prod_id = int(pid)
        except (ValueError, TypeError):
            continue
        prod = db.query(Product).filter_by(id=prod_id).first()
        if not prod:
            continue
        if prod.stock < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{prod.title}' (Requested: {qty}, Available: {prod.stock})"
            )
        prod.stock -= qty
        line_total = prod.price * qty
        total += line_total
        db.add(OrderItem(order_id=order.id, product_id=prod.id, quantity=qty, price=prod.price))

    order.total = round(total, 2)
    db.commit()

    # Clear cart and persist
    request.session["cart"] = {}

    return {"status": "order_created", "order_id": order.id, "total": order.total}
