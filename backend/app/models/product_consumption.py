"""
商品消费记录模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ProductConsumption(Base):
    """商品消费记录表"""
    __tablename__ = "product_consumptions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("room_sessions.id"), nullable=False, index=True, comment="房间使用记录ID")
    customer_id = Column(Integer, ForeignKey("customers.id"), comment="客户ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True, comment="商品ID")
    quantity = Column(Integer, nullable=False, comment="数量")
    unit_price = Column(Numeric(10, 2), nullable=False, comment="单价")
    total_price = Column(Numeric(10, 2), nullable=False, comment="总价")
    cost_price = Column(Numeric(10, 2), nullable=False, comment="成本价")
    total_cost = Column(Numeric(10, 2), nullable=False, comment="总成本")
    payment_method = Column(String(100), default="现金", comment="支付方式：现金、微信、支付宝、转账")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    session = relationship("RoomSession", back_populates="product_consumptions")
    customer = relationship("Customer")
    product = relationship("Product", back_populates="consumptions")

    __table_args__ = (
        Index("idx_product_consumptions_session_id", "session_id"),
        Index("idx_product_consumptions_product_id", "product_id"),
    )















