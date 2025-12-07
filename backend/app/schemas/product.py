"""
商品相关的Pydantic模型
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


class ProductBase(BaseModel):
    """商品基础模型"""
    name: str = Field(..., description="名称", max_length=100)
    unit: Optional[str] = Field(None, description="单位", max_length=20)
    price: Decimal = Field(..., ge=0, description="单价（销售价）")
    cost_price: Decimal = Field(..., ge=0, description="成本价")
    stock: int = Field(0, description="库存（允许负库存）")
    is_active: bool = Field(True, description="是否启用")
    product_type: str = Field("normal", description="商品类型：normal=普通商品, meal=餐费类型")


class ProductCreate(ProductBase):
    """创建商品模型"""
    pass


class ProductUpdate(BaseModel):
    """更新商品模型"""
    name: Optional[str] = Field(None, description="名称", max_length=100)
    unit: Optional[str] = Field(None, description="单位", max_length=20)
    price: Optional[Decimal] = Field(None, ge=0, description="单价")
    cost_price: Optional[Decimal] = Field(None, ge=0, description="成本价")
    stock: Optional[int] = Field(None, description="库存（允许负库存）")
    is_active: Optional[bool] = Field(None, description="是否启用")
    product_type: Optional[str] = Field(None, description="商品类型")


class ProductResponse(ProductBase):
    """商品响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        if dt is None:
            return ""
        return format_datetime_local(dt)


class StockAdjust(BaseModel):
    """库存调整模型"""
    adjustment: int = Field(..., description="调整数量（正数为增加，负数为减少）")









