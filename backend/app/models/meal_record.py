"""
餐费记录模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class MealRecord(Base):
    """餐费记录表"""
    __tablename__ = "meal_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("room_sessions.id"), nullable=False, comment="房间使用记录ID")
    customer_id = Column(Integer, ForeignKey("customers.id"), comment="客户ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="餐费商品ID")
    amount = Column(Numeric(10, 2), nullable=False, comment="餐费金额")
    cost_price = Column(Numeric(10, 2), nullable=False, comment="成本价")
    payment_method = Column(String(20), default="现金", comment="支付方式：现金、微信、支付宝、转账")
    description = Column(String(255), comment="餐费说明")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    session = relationship("RoomSession", back_populates="meal_records")
    customer = relationship("Customer")
    product = relationship("Product", back_populates="meal_records")















