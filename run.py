
"""Entrypoint to launch the Mini-Amazon Storefront application."""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  Mini-Amazon Storefront")
    print("  Local URL:   http://127.0.0.1:8000")
    print("  Network URL: http://192.168.0.161:8000")
    print("=" * 60)
    print("  Demo Credentials:")
    print("  - Customer: username='demo_user' | password='demo123'")
    print("  - Admin:    username='admin'     | password='admin123'")
    print("=" * 60)

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
