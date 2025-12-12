"""
供货商管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.db.database import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import (
    SupplierCreate, SupplierUpdate, SupplierResponse
)

router = APIRouter(prefix="/api/suppliers", tags=["供货商管理"])


@router.get("", response_model=List[SupplierResponse])
def get_suppliers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取供货商列表"""
    query = db.query(Supplier)
    
    if search:
        query = query.filter(
            or_(
                Supplier.name.like(f"%{search}%"),
                Supplier.contact.like(f"%{search}%"),
                Supplier.phone.like(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(Supplier.is_active == is_active)
    
    suppliers = query.offset(skip).limit(limit).all()
    return suppliers


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """获取供货商详情"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供货商不存在")
    return supplier


@router.post("", response_model=SupplierResponse)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    """创建供货商"""
    # 检查名称是否已存在
    existing_supplier = db.query(Supplier).filter(Supplier.name == supplier.name).first()
    if existing_supplier:
        raise HTTPException(status_code=400, detail="供货商名称已存在")
    
    db_supplier = Supplier(**supplier.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    supplier_update: SupplierUpdate,
    db: Session = Depends(get_db)
):
    """更新供货商"""
    db_supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="供货商不存在")
    
    # 检查名称是否被其他供货商使用
    if supplier_update.name and supplier_update.name != db_supplier.name:
        existing_supplier = db.query(Supplier).filter(
            Supplier.name == supplier_update.name,
            Supplier.id != supplier_id
        ).first()
        if existing_supplier:
            raise HTTPException(status_code=400, detail="供货商名称已被使用")
    
    update_data = supplier_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_supplier, field, value)
    
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """删除供货商"""
    db_supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="供货商不存在")
    
    # 检查是否有进货记录
    if db_supplier.purchases:
        raise HTTPException(status_code=400, detail="该供货商存在进货记录，无法删除")
    
    db.delete(db_supplier)
    db.commit()
    return {"message": "供货商已删除"}


