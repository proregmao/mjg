"""
房间客户关联模型
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class RoomCustomer(Base):
    """房间客户关联表"""
    __tablename__ = "room_customers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("room_sessions.id"), nullable=False, comment="房间使用记录ID")
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, comment="客户ID")
    joined_at = Column(DateTime(timezone=True), nullable=False, comment="加入时间")
    left_at = Column(DateTime(timezone=True), comment="离开时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    session = relationship("RoomSession", back_populates="room_customers")
    customer = relationship("Customer", back_populates="room_customers")
















