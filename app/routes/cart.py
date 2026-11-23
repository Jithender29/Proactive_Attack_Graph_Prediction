from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..db import Product
from ..middleware import get_db
from ..templates_config import render_template

router = APIRouter()


def _get_cart(request: Request) -> dict:
    cart = request.session.get("cart")
    if not isinstance(cart, dict):
        cart = {}
    return cart


def _save_cart(request: Request, cart: dict):
    # Reassigning directly to request.session triggers __setitem__ / mark_modified()
    request.session["cart"] = dict(cart)


@router.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request, db: Session = Depends(get_db)):
    cart = _get_cart(request)
    items = []
    subtotal = 0.0

    for pid, qty in cart.items():
        try:
            p_id_int = int(pid)
        except (ValueError, TypeError):
            continue
        prod = db.query(Product).filter_by(id=p_id_int).first()
        if not prod:
            continue
        total_price = prod.price * qty
        subtotal += total_price
        items.append({
            "product": prod,
            "quantity": qty,
            "total_price": round(total_price, 2),
        })

    return render_template(
        "cart.html",
        request=request,
        context={"items": items, "subtotal": round(subtotal, 2)},
        db=db,
    )


@router.get("/api/cart")
def api_get_cart(request: Request, db: Session = Depends(get_db)):
    cart = _get_cart(request)
    result = []
    for pid, qty in cart.items():
        try:
            p_id_int = int(pid)
        except (ValueError, TypeError):
            continue
        prod = db.query(Product).filter_by(id=p_id_int).first()
        if not prod:
            continue
        result.append({
            "product_id": prod.id,
            "title": prod.title,
            "price": prod.price,
            "quantity": qty,
            "total": round(prod.price * qty, 2),
        })
    return result


@router.post("/api/cart/add")
def api_add_to_cart(request: Request, product_id: int, quantity: int = 1):
    cart = _get_cart(request)
    pid = str(product_id)
    cart[pid] = cart.get(pid, 0) + max(1, quantity)
    _save_cart(request, cart)
    return {"status": "added", "product_id": product_id, "quantity": cart[pid], "total_items": sum(cart.values())}


@router.post("/api/cart/update")
def api_update_cart(request: Request, product_id: int, quantity: int):
    cart = _get_cart(request)
    pid = str(product_id)
    if quantity <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = quantity
    _save_cart(request, cart)
    return {"status": "updated", "product_id": product_id, "quantity": cart.get(pid, 0), "total_items": sum(cart.values())}


@router.post("/api/cart/remove")
def api_remove_from_cart(request: Request, product_id: int):
    cart = _get_cart(request)
    pid = str(product_id)
    cart.pop(pid, None)
    _save_cart(request, cart)
    return {"status": "removed", "product_id": product_id, "total_items": sum(cart.values())}
