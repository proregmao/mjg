"""
客户还款记录模型
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class CustomerRepayment(Base):
    """客户还款记录表"""
    __tablename__ = "customer_repayments"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, comment="客户ID")
    loan_id = Column(Integer, ForeignKey("customer_loans.id"), comment="借款记录ID")
    amount = Column(Numeric(10, 2), nullable=False, comment="还款金额")
    payment_method = Column(String(100), comment="还款方式：现金、微信、支付宝、转账")
    description = Column(String(500), comment="说明（可编辑）")
    session_id = Column(Integer, ForeignKey("room_sessions.id"), comment="房间使用记录ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    customer = relationship("Customer", back_populates="repayments")
    loan = relationship("CustomerLoan")
    session = relationship("RoomSession", back_populates="repayments")














