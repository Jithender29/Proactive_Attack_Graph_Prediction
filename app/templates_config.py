from pathlib import Path
from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .db import Category, User

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_template_context(request: Request, db: Session | None = None, custom_context: dict | None = None) -> dict:
    """Builds a standardized context containing user, categories, and cart count."""
    context = {"request": request}
    if custom_context:
        context.update(custom_context)

    # 1. User
    if "user" not in context or context["user"] is None:
        user_id = request.session.get("user_id")
        if user_id and db is not None:
            context["user"] = db.query(User).filter_by(id=user_id).first()
        else:
            context["user"] = None

    # 2. Categories
    if "categories" not in context or context["categories"] is None:
        if db is not None:
            context["categories"] = db.query(Category).order_by(Category.name).all()
        else:
            context["categories"] = []

    # 3. Live Cart count
    if "cart_count" not in context:
        cart = request.session.get("cart", {})
        if isinstance(cart, dict):
            context["cart_count"] = sum(v for v in cart.values() if isinstance(v, (int, float)))
        else:
            context["cart_count"] = 0

    return context


def render_template(
    template_name: str,
    request: Request,
    context: dict | None = None,
    db: Session | None = None,
    status_code: int = 200,
):
    """Safely renders a Jinja2 template using FastAPI/Starlette keyword syntax."""
    full_context = get_template_context(request, db=db, custom_context=context)
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=full_context,
        status_code=status_code,
    )
