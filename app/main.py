
import uvicorn
import sqlite3
import time
import hashlib
import datetime

from pathlib import Path
from fastapi import FastAPI, Request
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


# --------------------------------------------------
# SESSION MIDDLEWARE
# --------------------------------------------------

app.add_middleware(
    SessionMiddleware,
    secret_key="mini-amazon-demo-secure-session-key-change-in-prod",
    session_cookie="mini_amazon_session",
    max_age=14 * 24 * 3600,
)


# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


# --------------------------------------------------
# REGISTER ROUTERS
# --------------------------------------------------

app.include_router(home.router)
app.include_router(products.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(admin.router)


# --------------------------------------------------
# SECURITY EVENT LOGGING MIDDLEWARE
# --------------------------------------------------

@app.middleware("http")
async def security_event_logger(request: Request, call_next):
    """
    Record HTTP request metadata in SQLite
    for local security monitoring.
    """

    start_time = time.perf_counter()

    ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    # Generate a browser fingerprint.
    user_agent = request.headers.get("user-agent", "")

    fingerprint_source = f"{ip}|{user_agent}"

    session_fingerprint = hashlib.sha256(
        fingerprint_source.encode("utf-8")
    ).hexdigest()

    status_code = 500

    try:
        response = await call_next(request)

        status_code = response.status_code

        return response

    finally:
        duration_ms = (
            time.perf_counter() - start_time
        ) * 1000

        timestamp = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(timespec="milliseconds")

        try:
            with sqlite3.connect(
                str(db.SQLITE_PATH),
                timeout=5
            ) as conn:

                conn.execute("""
                    INSERT INTO events (
                        timestamp,
                        method,
                        route,
                        status_code,
                        ip,
                        session_fingerprint,
                        duration_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    request.method,
                    request.url.path,
                    status_code,
                    ip,
                    session_fingerprint,
                    duration_ms
                ))

                conn.commit()

        except Exception as exc:
            print(f"[EVENT LOGGER ERROR] {exc}")


# --------------------------------------------------
# APPLICATION STARTUP
# --------------------------------------------------

@app.on_event("startup")
def startup_event():
    """
    Initialize database tables and seed catalog data.
    """

    db.init_db()
    seed.seed_all()

    print("[DATABASE] Database initialized successfully.")
    print("[SECURITY] HTTP event logging enabled.")
    print("[SECURITY] Events are stored in store.db.")


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
