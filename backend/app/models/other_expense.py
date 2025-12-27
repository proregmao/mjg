"""
其它支出模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.sql import func
from app.db.database import Base


class OtherExpense(Base):
    """其它支出表"""
    __tablename__ = "other_expenses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="支出名称")
    amount = Column(Numeric(10, 2), nullable=False, comment="支出金额")
    payment_method = Column(String(100), default="现金", comment="支付方式：现金、微信、支付宝、转账")
    description = Column(Text, comment="备注说明")
    expense_date = Column(DateTime(timezone=True), nullable=False, comment="支出日期")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")











