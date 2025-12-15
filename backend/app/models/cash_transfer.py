"""
现金转账模型（从银行取现/存入银行）
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.sql import func
from app.db.database import Base


class CashTransfer(Base):
    """现金转账表（从银行取现/存入银行）"""
    __tablename__ = "cash_transfers"

    id = Column(Integer, primary_key=True, index=True)
    transfer_type = Column(String(20), nullable=False, comment="转账类型：bank_to_cash=从银行取现, cash_to_bank=存入银行")
    amount = Column(Numeric(10, 2), nullable=False, comment="转账金额")
    description = Column(Text, comment="备注说明")
    transfer_date = Column(DateTime(timezone=True), nullable=False, comment="转账日期")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")



