import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import db, seed
from .templates_config import templates
from .routes import home, products, auth, cart, checkout, orders, admin

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="Mini-Amazon Storefront",
    description="A lightweight, clean mini Amazon e-commerce storefront prototype",
    version="1.0.0",
)

# Cookie-based session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="mini-amazon-demo-secure-session-key-change-in-prod",
    session_cookie="mini_amazon_session",
    max_age=14 * 24 * 3600,  # 14 days
)

# Static files mounting
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Register modular routers
app.include_router(home.router)
app.include_router(products.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup_event():
    """Ensure database tables exist and dummy catalog data is seeded."""
    db.init_db()
    seed.seed_all()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
