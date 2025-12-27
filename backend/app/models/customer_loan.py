"""
客户借款记录模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class CustomerLoan(Base):
    """客户借款记录表"""
    __tablename__ = "customer_loans"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True, comment="客户ID")
    amount = Column(Numeric(10, 2), nullable=False, comment="借款金额")
    loan_type = Column(String(100), nullable=False, comment="借款类型：from_shop=向麻将馆借款, between_customers=客户间借款")
    from_customer_id = Column(Integer, ForeignKey("customers.id"), comment="出借方客户ID")
    to_customer_id = Column(Integer, ForeignKey("customers.id"), comment="借入方客户ID")
    transfer_from_id = Column(Integer, ForeignKey("transfers.id"), comment="转移款关联ID")
    status = Column(String(100), default="active", index=True, comment="状态：active=正常, transferred=已转移, repaid=已还清")
    remaining_amount = Column(Numeric(10, 2), nullable=False, comment="剩余未还金额")
    payment_method = Column(String(100), comment="支付方式：现金、微信、支付宝、转账")
    description = Column(String(500), comment="说明（可编辑）")
    session_id = Column(Integer, ForeignKey("room_sessions.id"), comment="房间使用记录ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关系
    customer = relationship("Customer", back_populates="loans", foreign_keys=[customer_id])
    session = relationship("RoomSession", back_populates="loans")

    __table_args__ = (
        Index("idx_customer_loans_customer_id", "customer_id"),
        Index("idx_customer_loans_status", "status"),
    )

