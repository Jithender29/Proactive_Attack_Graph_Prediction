from pathlib import Path
from sqlalchemy import (Column, Integer, String, Float, Boolean,
                        ForeignKey, DateTime, Text, create_engine)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime

BASE_DIR = Path(__file__).parent.parent
SQLITE_PATH = BASE_DIR / "store.db"

engine = create_engine(f"sqlite:///{SQLITE_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # plaintext for demo only
    is_admin = Column(Boolean, default=False)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    image_url = Column(String, default="/static/placeholder.png")
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", backref="products")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    total = Column(Float, nullable=False)
    user = relationship("User", backref="orders")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)  # snapshot price
    order = relationship("Order", backref="items")
    product = relationship("Product")

def init_db():
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
