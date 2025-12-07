"""
进货管理模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Purchase(Base):
    """进货单表"""
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True, comment="供货商ID")
    purchase_date = Column(Date, nullable=False, index=True, comment="进货日期")
    total_amount = Column(Numeric(10, 2), nullable=False, default=0, comment="总金额")
    notes = Column(String(500), comment="备注")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关系
    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_purchases_supplier_id", "supplier_id"),
        Index("idx_purchases_purchase_date", "purchase_date"),
    )


class PurchaseItem(Base):
    """进货明细表"""
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False, index=True, comment="进货单ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True, comment="商品ID")
    quantity = Column(Integer, nullable=False, comment="进货数量")
    unit_price = Column(Numeric(10, 2), nullable=False, comment="进货单价")
    total_price = Column(Numeric(10, 2), nullable=False, comment="小计金额")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")

    __table_args__ = (
        Index("idx_purchase_items_purchase_id", "purchase_id"),
        Index("idx_purchase_items_product_id", "product_id"),
    )

