"""
系统配置相关的Pydantic模型
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


class SystemConfigCreate(BaseModel):
    """创建系统配置模型"""
    key: str = Field(..., description="配置键", max_length=100)
    value: str = Field(..., description="配置值", max_length=500)
    description: Optional[str] = Field(None, description="配置说明", max_length=200)


class SystemConfigUpdate(BaseModel):
    """更新系统配置模型"""
    value: Optional[str] = Field(None, description="配置值", max_length=500)
    description: Optional[str] = Field(None, description="配置说明", max_length=200)


class SystemConfigResponse(BaseModel):
    """系统配置响应模型"""
    id: int
    key: str
    value: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)









