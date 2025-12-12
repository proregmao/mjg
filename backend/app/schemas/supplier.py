"""
供货商相关的Pydantic模型
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime, timezone, timedelta

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


class SupplierBase(BaseModel):
    """供货商基础模型"""
    name: str = Field(..., description="供货商名称", max_length=100)
    contact: Optional[str] = Field(None, description="联系人", max_length=50)
    phone: Optional[str] = Field(None, description="联系电话", max_length=20)
    address: Optional[str] = Field(None, description="地址", max_length=255)
    notes: Optional[str] = Field(None, description="备注", max_length=500)
    is_active: bool = Field(True, description="是否启用")


class SupplierCreate(SupplierBase):
    """创建供货商模型"""
    pass


class SupplierUpdate(BaseModel):
    """更新供货商模型"""
    name: Optional[str] = Field(None, description="供货商名称", max_length=100)
    contact: Optional[str] = Field(None, description="联系人", max_length=50)
    phone: Optional[str] = Field(None, description="联系电话", max_length=20)
    address: Optional[str] = Field(None, description="地址", max_length=255)
    notes: Optional[str] = Field(None, description="备注", max_length=500)
    is_active: Optional[bool] = Field(None, description="是否启用")


class SupplierResponse(SupplierBase):
    """供货商响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)


