"""
客户相关的Pydantic模型
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
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


class CustomerBase(BaseModel):
    """客户基础模型"""
    name: str = Field(..., description="姓名", max_length=100)
    phone: Optional[str] = Field(None, description="电话", max_length=20)


class CustomerCreate(CustomerBase):
    """创建客户模型"""
    initial_balance: Optional[Decimal] = Field(0, description="初期帐单(正数存款负数欠款)")


class CustomerUpdate(BaseModel):
    """更新客户模型"""
    name: Optional[str] = Field(None, description="姓名", max_length=100)
    phone: Optional[str] = Field(None, description="电话", max_length=20)


class CustomerResponse(CustomerBase):
    """客户响应模型"""
    id: int
    initial_balance: Decimal = Field(0, description="初期帐单(正数存款负数欠款)")
    balance: Decimal = Field(..., description="当前欠款余额")
    deposit: Decimal = Field(..., description="存款余额")
    is_deleted: Optional[int] = Field(0, description="是否已删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")
    created_at: datetime
    session_count: Optional[int] = Field(0, description="参与场次")
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at', 'deleted_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)


class CustomerTransfer(BaseModel):
    """客户转账模型"""
    from_customer_id: int = Field(..., description="转出方客户ID")
    to_customer_id: int = Field(..., description="转入方客户ID")
    amount: Decimal = Field(..., gt=0, description="转移金额")


class CustomerBatchDelete(BaseModel):
    """批量删除客户模型"""
    ids: List[int] = Field(..., description="要删除的客户ID列表")




