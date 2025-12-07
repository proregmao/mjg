"""
转账记录模型
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Transfer(Base):
    """转账记录表"""
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    from_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, comment="转出方客户ID")
    to_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, comment="转入方客户ID")
    amount = Column(Numeric(10, 2), nullable=False, comment="转移金额")
    original_loan_id = Column(Integer, ForeignKey("customer_loans.id"), nullable=False, comment="原始借款记录ID")
    new_loan_id = Column(Integer, ForeignKey("customer_loans.id"), nullable=False, comment="新创建的借款记录ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    from_customer = relationship("Customer", back_populates="transfers_from", foreign_keys=[from_customer_id])
    to_customer = relationship("Customer", back_populates="transfers_to", foreign_keys=[to_customer_id])
    original_loan = relationship("CustomerLoan", foreign_keys=[original_loan_id])
    new_loan = relationship("CustomerLoan", foreign_keys=[new_loan_id])

