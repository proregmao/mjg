"""
借款相关的Pydantic模型
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))


def format_datetime_local(dt: datetime) -> str:
    """将UTC时间转换为本地时间字符串"""
    if dt is None:
        return None
    # 如果时间没有时区信息，假设它是 UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # 转换为中国时区
    local_dt = dt.astimezone(CHINA_TZ)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


class LoanResponse(BaseModel):
    """借款记录响应模型"""
    id: int
    customer_id: int
    amount: Decimal
    loan_type: str
    from_customer_id: Optional[int] = None
    to_customer_id: Optional[int] = None
    status: str
    remaining_amount: Decimal
    payment_method: Optional[str] = None
    session_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)


class RepaymentResponse(BaseModel):
    """还款记录响应模型"""
    id: int
    customer_id: int
    loan_id: Optional[int] = None
    amount: Decimal
    payment_method: Optional[str] = None
    session_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)


class LoanCreate(BaseModel):
    """创建借款模型"""
    customer_id: int = Field(..., description="客户ID")
    amount: Decimal = Field(..., gt=0, description="借款金额")
    session_id: Optional[int] = Field(None, description="房间使用记录ID")


class RepaymentCreate(BaseModel):
    """创建还款模型"""
    customer_id: int = Field(..., description="客户ID")
    amount: Decimal = Field(..., ne=0, description="还款金额（正数为还款，负数为退款/支付）")
    payment_method: Optional[str] = Field(None, description="还款方式：现金、微信、支付宝、转账")
    loan_id: Optional[int] = Field(None, description="借款记录ID（可选，不填则还总欠款）")
    session_id: Optional[int] = Field(None, description="房间使用记录ID")









