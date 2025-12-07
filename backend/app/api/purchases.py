"""
进货管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date
from decimal import Decimal
from app.db.database import get_db
from app.models.purchase import Purchase, PurchaseItem
from app.models.supplier import Supplier
from app.models.product import Product
from app.schemas.purchase import (
    PurchaseCreate, PurchaseUpdate, PurchaseResponse, PurchaseItemResponse
)

router = APIRouter(prefix="/api/purchases", tags=["进货管理"])


def update_product_stock_and_cost(product: Product, quantity: int, unit_price: Decimal):
    """更新商品库存和成本价（加权平均）"""
    # 增加库存
    product.stock = product.stock + quantity
    
    # 计算加权平均成本价
    # 新成本价 = (原库存*原成本价 + 进货数量*进货单价) / (原库存+进货数量)
    if product.stock > 0:
        old_stock = product.stock - quantity
        if old_stock > 0:
            # 加权平均
            new_cost_price = (old_stock * product.cost_price + quantity * unit_price) / product.stock
        else:
            # 如果原库存为0，直接使用进货单价
            new_cost_price = unit_price
        product.cost_price = new_cost_price


@router.get("", response_model=List[PurchaseResponse])
def get_purchases(
    skip: int = 0,
    limit: int = 100,
    supplier_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """获取进货单列表"""
    query = db.query(Purchase)
    
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    
    if start_date:
        query = query.filter(Purchase.purchase_date >= start_date)
    
    if end_date:
        query = query.filter(Purchase.purchase_date <= end_date)
    
    purchases = query.order_by(Purchase.purchase_date.desc()).offset(skip).limit(limit).all()
    
    # 添加供货商名称
    result = []
    for purchase in purchases:
        purchase_dict = {
            **purchase.__dict__,
            "supplier_name": purchase.supplier.name if purchase.supplier else None,
            "items": []
        }
        # 添加明细
        for item in purchase.items:
            item_dict = {
                **item.__dict__,
                "product_name": item.product.name if item.product else None
            }
            purchase_dict["items"].append(item_dict)
        result.append(purchase_dict)
    
    return result


@router.get("/{purchase_id}", response_model=PurchaseResponse)
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    """获取进货单详情"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="进货单不存在")
    
    # 构建响应数据
    purchase_dict = {
        **purchase.__dict__,
        "supplier_name": purchase.supplier.name if purchase.supplier else None,
        "items": []
    }
    
    # 添加明细
    for item in purchase.items:
        item_dict = {
            **item.__dict__,
            "product_name": item.product.name if item.product else None
        }
        purchase_dict["items"].append(item_dict)
    
    return purchase_dict


@router.post("", response_model=PurchaseResponse)
def create_purchase(purchase: PurchaseCreate, db: Session = Depends(get_db)):
    """创建进货单"""
    # 验证供货商是否存在
    supplier = db.query(Supplier).filter(Supplier.id == purchase.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供货商不存在")
    
    if not supplier.is_active:
        raise HTTPException(status_code=400, detail="供货商已禁用")
    
    # 验证商品并计算总金额
    total_amount = Decimal(0)
    items_to_create = []
    
    for item in purchase.items:
        # 验证商品是否存在
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"商品ID {item.product_id} 不存在")
        
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"商品 {product.name} 已禁用")
        
        # 计算小计
        item_total = item.quantity * item.unit_price
        total_amount += item_total
        
        items_to_create.append({
            "product": product,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total_price": item_total
        })
    
    # 创建进货单
    db_purchase = Purchase(
        supplier_id=purchase.supplier_id,
        purchase_date=purchase.purchase_date,
        total_amount=total_amount,
        notes=purchase.notes
    )
    db.add(db_purchase)
    db.flush()  # 获取ID
    
    # 创建进货明细并更新商品库存
    for item_data in items_to_create:
        # 创建明细
        purchase_item = PurchaseItem(
            purchase_id=db_purchase.id,
            product_id=item_data["product"].id,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"]
        )
        db.add(purchase_item)
        
        # 更新商品库存和成本价
        update_product_stock_and_cost(
            item_data["product"],
            item_data["quantity"],
            item_data["unit_price"]
        )
    
    db.commit()
    db.refresh(db_purchase)
    
    # 返回完整数据
    return get_purchase(db_purchase.id, db)


@router.delete("/{purchase_id}")
def delete_purchase(purchase_id: int, db: Session = Depends(get_db)):
    """删除进货单（需要回退库存和成本价，通常不建议删除）"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="进货单不存在")
    
    # 回退库存（简化处理：直接减少库存，不处理成本价回退）
    for item in purchase.items:
        product = item.product
        if product:
            # 减少库存
            product.stock = max(0, product.stock - item.quantity)
    
    db.delete(purchase)
    db.commit()
    return {"message": "进货单已删除"}


@router.get("/product/{product_id}/history")
def get_product_purchase_history(
    product_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取商品的进货历史"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    # 查询该商品的进货明细
    items = db.query(PurchaseItem).filter(
        PurchaseItem.product_id == product_id
    ).order_by(PurchaseItem.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "purchase_id": item.purchase_id,
            "purchase_date": item.purchase.created_at.date() if item.purchase else None,
            "supplier_name": item.purchase.supplier.name if item.purchase and item.purchase.supplier else None,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "total_price": float(item.total_price),
            "created_at": item.created_at
        })
    
    return result

