from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..db import Product, Category
from ..middleware import get_db
from ..templates_config import render_template

router = APIRouter()


@router.get("/products", response_class=HTMLResponse)
def product_list(
    request: Request,
    category: int = Query(None),
    q: str = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category_id == category)
    if q:
        search_term = f"%{q}%"
        query = query.filter(Product.title.ilike(search_term) | Product.description.ilike(search_term))
    products = query.all()
    categories = db.query(Category).order_by(Category.name).all()

    return render_template(
        "home.html",
        request=request,
        context={
            "categories": categories,
            "featured": products,
            "selected_category": category,
            "search_query": q,
        },
        db=db,
    )


@router.get("/api/products")
def api_product_list(
    category: int = Query(None),
    q: str = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category_id == category)
    if q:
        query = query.filter(Product.title.ilike(f"%{q}%") | Product.description.ilike(f"%{q}%"))
    products = query.all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "price": p.price,
            "stock": p.stock,
            "rating": p.rating,
            "image_url": p.image_url,
            "category_id": p.category_id,
            "category_name": p.category.name if p.category else "",
        }
        for p in products
    ]


@router.get("/api/search")
def api_search(q: str = Query(""), db: Session = Depends(get_db)):
    term = f"%{q}%"
    products = (
        db.query(Product)
        .outerjoin(Category)
        .filter(
            Product.title.ilike(term)
            | Product.description.ilike(term)
            | Category.name.ilike(term)
        )
        .all()
    )
    return [
        {
            "id": p.id,
            "title": p.title,
            "price": p.price,
            "stock": p.stock,
            "rating": p.rating,
            "category_id": p.category_id,
            "category_name": p.category.name if p.category else "",
        }
        for p in products
    ]


@router.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter_by(id=product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return render_template(
        "product_detail.html",
        request=request,
        context={"product": prod},
        db=db,
    )


@router.get("/api/products/{product_id}")
def api_product_detail(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter_by(id=product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": prod.id,
        "title": prod.title,
        "description": prod.description,
        "price": prod.price,
        "stock": prod.stock,
        "rating": prod.rating,
        "image_url": prod.image_url,
        "category_id": prod.category_id,
        "category_name": prod.category.name if prod.category else "",
    }
