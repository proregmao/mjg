"""
商品管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.db.database import get_db
from app.models.product import Product
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, StockAdjust
)

router = APIRouter(prefix="/api/products", tags=["商品管理"])


@router.get("", response_model=List[ProductResponse])
def get_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    product_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取商品列表"""
    query = db.query(Product)
    
    if search:
        query = query.filter(Product.name.like(f"%{search}%"))
    
    if product_type:
        query = query.filter(Product.product_type == product_type)
    
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    products = query.offset(skip).limit(limit).all()
    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """获取商品详情"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """创建商品"""
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db)
):
    """更新商品"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    update_data = product_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """删除商品（真正删除，如果有关联记录则不允许删除）"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    # 检查是否有商品消费记录
    consumption_count = db.query(ProductConsumption).filter(
        ProductConsumption.product_id == product_id
    ).count()
    
    if consumption_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"该商品已有 {consumption_count} 条消费记录，无法删除"
        )
    
    # 检查是否有餐费记录
    meal_count = db.query(MealRecord).filter(
        MealRecord.product_id == product_id
    ).count()
    
    if meal_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"该商品已有 {meal_count} 条餐费记录，无法删除"
        )
    
    # 真正删除商品
    db.delete(db_product)
    db.commit()
    return {"message": "商品已删除"}


@router.put("/{product_id}/stock", response_model=ProductResponse)
def adjust_stock(
    product_id: int,
    stock_adjust: StockAdjust,
    db: Session = Depends(get_db)
):
    """调整库存"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    new_stock = db_product.stock + stock_adjust.adjustment
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="库存不足，无法减少")
    
    db_product.stock = new_stock
    db.commit()
    db.refresh(db_product)
    return db_product









