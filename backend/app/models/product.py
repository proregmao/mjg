"""
商品模型
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Product(Base):
    """商品表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, comment="名称")
    unit = Column(String(20), comment="单位")
    price = Column(Numeric(10, 2), nullable=False, comment="单价（销售价）")
    cost_price = Column(Numeric(10, 2), nullable=False, comment="成本价")
    stock = Column(Integer, default=0, comment="库存")
    is_active = Column(Boolean, default=True, comment="是否启用")
    product_type = Column(String(20), default="normal", comment="商品类型：normal=普通商品, meal=餐费类型")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关系
    consumptions = relationship("ProductConsumption", back_populates="product")
    meal_records = relationship("MealRecord", back_populates="product")
    purchase_items = relationship("PurchaseItem", back_populates="product")

    __table_args__ = (
        Index("idx_products_name", "name"),
    )

