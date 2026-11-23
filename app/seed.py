from .db import SessionLocal, User, Category, Product, Order, OrderItem
import random

def seed_all():
    db = SessionLocal()
    try:
        # Users
        if not db.query(User).first():
            db.add_all([
                User(username="demo_user", password="demo123", is_admin=False),
                User(username="admin", password="admin123", is_admin=True),
            ])
        # Categories
        cat_names = ["Electronics", "Home & Kitchen", "Books", "Fashion", "Fitness"]
        if not db.query(Category).first():
            categories = [Category(name=n) for n in cat_names]
            db.add_all(categories)
            db.flush()
        # Products
        if not db.query(Product).first():
            cat_map = {c.name: c for c in db.query(Category).all()}
            base = [
                {"title": "Wireless Bluetooth Headphones", "price": 49.99, "stock": 27, "rating": 4.3, "category": "Electronics"},
                {"title": "LED Desk Lamp with USB Charger", "price": 29.95, "stock": 42, "rating": 4.6, "category": "Home & Kitchen"},
                {"title": "Water‑Resistant Backpack 30L", "price": 39.99, "stock": 15, "rating": 4.1, "category": "Fashion"},
                {"title": "Stainless Steel French Press Coffee Maker", "price": 24.99, "stock": 33, "rating": 4.5, "category": "Home & Kitchen"},
                {"title": "Yoga Mat – Extra Thick, Non‑Slip", "price": 19.99, "stock": 58, "rating": 4.7, "category": "Fitness"},
                {"title": "Best‑Selling Novel: \"The Silent City\"", "price": 12.99, "stock": 70, "rating": 4.2, "category": "Books"},
            ]
            products = []
            for p in base:
                prod = Product(
                    title=p["title"],
                    description=f"A high‑quality {p['title'].lower()}.",
                    price=p["price"],
                    stock=p["stock"],
                    rating=p["rating"],
                    category_id=cat_map[p["category"]].id,
                )
                products.append(prod)
            # duplicate to reach 20‑25 items
            while len(products) < 20:
                src = random.choice(products)
                copy = Product(
                    title=src.title + " (Variant)",
                    description=src.description,
                    price=round(src.price * (0.9 + 0.2 * random.random()), 2),
                    stock=random.randint(5, 30),
                    rating=round(src.rating + random.uniform(-0.2, 0.2), 1),
                    category_id=src.category_id,
                )
                products.append(copy)
            db.add_all(products)
        # Demo order for demo_user
        if not db.query(Order).first():
            demo_user = db.query(User).filter_by(username="demo_user").first()
            order = Order(user_id=demo_user.id, total=0.0)
            db.add(order)
            db.flush()
            prod_ids = [p.id for p in db.query(Product).limit(5).all()]
            total = 0.0
            for pid in prod_ids[:2]:
                prod = db.query(Product).get(pid)
                item = OrderItem(order_id=order.id, product_id=pid, quantity=1, price=prod.price)
                db.add(item)
                total += prod.price
            order.total = round(total, 2)
        db.commit()
    finally:
        db.close()
