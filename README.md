# 🛒 Mini Amazon Storefront Web Application

A lightweight, modular, and fully functional e-commerce web application built with **FastAPI**, **Jinja2**, **SQLAlchemy**, and **SQLite**. Designed with a clean, familiar Amazon-inspired storefront interface, realistic synthetic catalog data, live session-based shopping cart, simulated checkout, order tracking, and an admin inventory management dashboard.

---

## 🌟 Key Features

### 1. Amazon-Inspired Storefront UI
- **Top Navigation Bar:** Brand logo, product search bar with integrated category selector, user account & lists dropdown, order history link, and a live cart badge with dynamic item count.
- **Category Navigation Strip:** Quick-filter pill links across *Electronics*, *Home & Kitchen*, *Books*, *Fashion*, and *Fitness*.
- **Featured Deals Grid:** Clean product cards featuring category-specific icon badges, product titles, star ratings (e.g. ⭐ 4.5), dollar pricing, stock status indicators (*In Stock*, *Only X left*, or *Out of stock*), and one-click **Add to Cart**.
- **Product Detail Page:** Breadcrumb navigation, detailed specifications, full item descriptions, simulated Amazon **Buy Box**, quantity selector, **Add to Cart**, and instant **Buy Now** flow.

### 2. Cart, Checkout & Orders
- **Shopping Cart (`/cart`):** Live quantity adjustments, line-item deletions, subtotal calculations, and free shipping qualification banners.
- **Simulated Checkout (`/checkout`):** Amazon-style multi-step review (delivery address, synthetic payment card preview, item summary, and order total) with simulated one-click order placement.
- **Order History (`/orders`):** Comprehensive order list displaying order IDs, timestamped order dates, synthetic delivery statuses, items purchased with quantities, and total spent.

### 3. Authentication & Roles
- **Session-Based State:** Managed via secure cookie-based signed sessions (`SessionMiddleware`).
- **Demo Accounts:** Pre-seeded customer and admin accounts with 1-click credential autofill buttons on the login page:
  - **Customer:** `username: demo_user` | `password: demo123`
  - **Administrator:** `username: admin` | `password: admin123`
- **Role-Based Protection:** Admin portal access is restricted; unauthorized requests return `401 Unauthorized` or `403 Forbidden`.

### 4. Admin Inventory Portal (`/admin`)
- Real-time catalog summary metrics (Total Products, Active Categories, and Low Stock Alerts).
- Tabular inventory view with color-coded stock health badges (*Healthy*, *Low*, *Out of Stock*).

### 5. Automatic Startup Seeding
- On initial startup, SQLite database (`store.db`) is automatically initialized and seeded with:
  - 2 demo user accounts
  - 5 everyday product categories
  - 20+ realistic products (wireless headphones, desk lamps, backpacks, coffee makers, yoga mats, books, etc.)
  - Mock past orders
- **Zero manual database setup required.** All data is synthetic dummy data with no live payment processing.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) |
| **ASGI Web Server** | [Uvicorn](https://www.uvicorn.org/) |
| **Database & ORM** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with SQLite |
| **Session Security** | [ItsDangerous](https://itsdangerous.palletsprojects.com/) + Starlette `SessionMiddleware` |
| **Templating Engine** | [Jinja2](https://jinja.palletsprojects.com/) |
| **Frontend** | HTML5, CSS3 (Amazon-themed responsive layout), Vanilla JavaScript |

---

## 📂 Project Structure

```text
Proactive_Attack_Graph_Prediction/
├── app/
│   ├── __init__.py               # Marks 'app' as a Python package
│   ├── main.py                   # FastAPI application initialization & route registration
│   ├── db.py                     # SQLAlchemy database engine, session & models
│   ├── seed.py                   # Automatic startup catalog & user seeding
│   ├── middleware.py             # FastAPI dependency injection helpers (e.g., get_db)
│   ├── templates_config.py       # Centralized Jinja2 template renderer & global context
│   │
│   ├── routes/                   # Modular route controllers
│   │   ├── __init__.py
│   │   ├── home.py               # Home storefront view (GET /)
│   │   ├── products.py           # Catalog, category filtering, search & detail (HTML & JSON API)
│   │   ├── auth.py               # Login, logout, profile & auth status (HTML & JSON API)
│   │   ├── cart.py               # Cart page & cart actions (add, update, remove JSON endpoints)
│   │   ├── checkout.py           # Checkout view & synthetic order placement API
│   │   ├── orders.py             # Order history view & order details API
│   │   └── admin.py              # Inventory management view & admin API
│   │
│   ├── templates/                # Jinja2 HTML templates
│   │   ├── base.html             # Common layout (Navbar, search bar, category strip, footer)
│   │   ├── home.html             # Homepage product grid & featured deals
│   │   ├── product_detail.html   # Product details, specs & Buy Box
│   │   ├── cart.html             # Shopping cart item table & subtotal summary
│   │   ├── checkout.html         # Multi-step checkout review & order button
│   │   ├── orders.html           # Past order history & tracking cards
│   │   ├── login.html            # Sign-in form with 1-click demo credential autofill
│   │   ├── profile.html          # User account overview & sign out
│   │   └── admin.html            # Real-time inventory dashboard
│   │
│   └── static/                   # Static web assets
│       ├── style.css             # Responsive Amazon-inspired stylesheet
│       └── script.js             # Cart updates, toast notifications & API handlers
│
├── requirements.txt              # Pinned Python package dependencies
├── run.py                        # Standalone runner script
└── README.md                     # Application documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher installed.

### Option 1: Quick Start (Direct Execution)
If dependencies are already installed globally on your machine:
```powershell
python run.py
```

### Option 2: Standard Virtual Environment Setup
To isolate project dependencies:

1. **Clone or navigate to the project directory:**
   ```powershell
   cd "d:\COLLEGE\Major project\Proactive_Attack_Graph_Prediction"
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   # Windows PowerShell:
   python -m venv venv
   .\venv\Scripts\Activate
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Launch the development server:**
   ```powershell
   python run.py
   ```
   *Alternatively, run Uvicorn directly:*
   ```powershell
   uvicorn app.main:app --reload
   ```

5. **Open your browser:**
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 🔑 Demo Credentials

| Role | Username | Password | Access Privileges |
|---|---|---|---|
| **Customer** | `demo_user` | `demo123` | Browsing, cart management, simulated checkout, past orders |
| **Administrator** | `admin` | `admin123` | Full customer capabilities + `/admin` inventory portal access |

*(Tip: The [Sign-In page](http://127.0.0.1:8000/login) includes one-click buttons to instantly autofill these credentials).*

---

## 🌐 API Route Reference

### Catalog & Search
| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/` | Storefront home page with deals and popular items | `200` |
| `GET` | `/products` | Catalog view with category & search query filters | `200` |
| `GET` | `/products/{id}` | Detailed product view | `200`, `404` |
| `GET` | `/api/products` | JSON list of products with optional `?category=` and `?q=` | `200` |
| `GET` | `/api/products/{id}` | Single product JSON details | `200`, `404` |
| `GET` | `/api/search?q=...` | Keyword search across titles, descriptions, and categories | `200` |

### Authentication & Account
| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/login` | Sign-in page with 1-click credential buttons | `200` |
| `POST` | `/login` | Form login processing | `302` (redirect), `401` (invalid) |
| `POST` | `/logout` | Clears active user session | `302` (redirect) |
| `GET` | `/profile` | User profile page (requires authentication) | `200`, `302` |
| `GET` | `/api/profile` | Current user profile details | `200`, `401` |

### Cart & Checkout
| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/cart` | Shopping cart view | `200` |
| `GET` | `/api/cart` | JSON representation of current session's cart items | `200` |
| `POST` | `/api/cart/add` | Adds product to cart (`?product_id=...&quantity=...`) | `200` |
| `POST` | `/api/cart/update` | Updates quantity of a cart item | `200` |
| `POST` | `/api/cart/remove` | Removes product from cart | `200` |
| `GET` | `/checkout` | Order review page (redirects if cart is empty) | `200`, `302` |
| `POST` | `/api/checkout` | Simulates order placement, deducts stock, clears cart | `200`, `400`, `401` |
| `GET` | `/orders` | Order history page | `200`, `302` |
| `GET` | `/api/orders/{id}` | JSON order summary and item breakdown | `200`, `401`, `403`, `404` |

### Administration
| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/admin` | Admin inventory monitoring dashboard | `200`, `401`, `403` |
| `GET` | `/api/admin/inventory` | JSON inventory report with stock levels | `200`, `401`, `403` |

---

## 🔒 Security & Privacy Notice
All user credentials, mock product records, order details, and addresses in this application are **synthetic demo placeholders**. No real financial transactions, payment gateways, or personally identifiable information (PII) are used or processed.
