"""
房间使用记录模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class RoomSession(Base):
    """房间使用记录表"""
    __tablename__ = "room_sessions"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True, comment="房间ID")
    start_time = Column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_time = Column(DateTime(timezone=True), comment="结束时间")
    status = Column(String(20), default="in_progress", index=True, comment="状态：in_progress=进行中, settled=已结算")
    table_fee = Column(Numeric(10, 2), default=0, comment="台子费")
    table_fee_payment_method = Column(String(20), default="现金", comment="台子费支付方式：现金、微信、支付宝、转账")
    total_revenue = Column(Numeric(10, 2), default=0, comment="总收入")
    total_cost = Column(Numeric(10, 2), default=0, comment="总成本")
    total_profit = Column(Numeric(10, 2), default=0, comment="总利润")
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True, comment="删除时间（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关系
    room = relationship("Room", back_populates="sessions")
    room_customers = relationship("RoomCustomer", back_populates="session")
    loans = relationship("CustomerLoan", back_populates="session")
    repayments = relationship("CustomerRepayment", back_populates="session")
    product_consumptions = relationship("ProductConsumption", back_populates="session")
    meal_records = relationship("MealRecord", back_populates="session")
    room_transfers = relationship("RoomTransfer", back_populates="session")

    __table_args__ = (
        Index("idx_room_sessions_room_id", "room_id"),
        Index("idx_room_sessions_status", "status"),
    )















