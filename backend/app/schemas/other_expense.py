"""
其它支出相关的Pydantic模型
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
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(CHINA_TZ)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


class OtherExpenseCreate(BaseModel):
    """创建其它支出模型"""
    name: str = Field(..., description="支出名称", max_length=200)
    amount: Decimal = Field(..., gt=0, description="支出金额")
    payment_method: Optional[str] = Field("现金", description="支付方式：现金、微信、支付宝、转账，默认为现金")
    description: Optional[str] = Field(None, description="备注说明")
    expense_date: datetime = Field(..., description="支出日期")


class OtherExpenseUpdate(BaseModel):
    """更新其它支出模型"""
    name: Optional[str] = Field(None, description="支出名称", max_length=200)
    amount: Optional[Decimal] = Field(None, gt=0, description="支出金额")
    payment_method: Optional[str] = Field(None, description="支付方式：现金、微信、支付宝、转账")
    description: Optional[str] = Field(None, description="备注说明")
    expense_date: Optional[datetime] = Field(None, description="支出日期")


class OtherExpenseResponse(BaseModel):
    """其它支出响应模型"""
    id: int
    name: str
    amount: Decimal
    payment_method: str
    description: Optional[str] = None
    expense_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('expense_date', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)











