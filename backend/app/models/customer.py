"""
客户模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Customer(Base):
    """客户表"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, comment="姓名")
    phone = Column(String(20), index=True, comment="电话")
    initial_balance = Column(Numeric(10, 2), default=0, comment="初期帐单(正数存款负数欠款)")
    balance = Column(Numeric(10, 2), nullable=False, default=0, comment="当前欠款余额")
    deposit = Column(Numeric(10, 2), default=0, comment="存款余额")
    is_deleted = Column(Integer, default=0, comment="是否已删除(0未删除1已删除)")
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="删除时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关系
    loans = relationship("CustomerLoan", back_populates="customer", foreign_keys="CustomerLoan.customer_id")
    repayments = relationship("CustomerRepayment", back_populates="customer")
    transfers_from = relationship("Transfer", back_populates="from_customer", foreign_keys="Transfer.from_customer_id")
    transfers_to = relationship("Transfer", back_populates="to_customer", foreign_keys="Transfer.to_customer_id")
    room_customers = relationship("RoomCustomer", back_populates="customer")

    __table_args__ = (
        Index("idx_customers_name", "name"),
        Index("idx_customers_phone", "phone"),
    )




