"""
进货管理相关的Pydantic模型
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime, date, timezone, timedelta
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


class PurchaseItemBase(BaseModel):
    """进货明细基础模型"""
    product_id: int = Field(..., description="商品ID")
    quantity: int = Field(..., gt=0, description="进货数量")
    unit_price: Decimal = Field(..., gt=0, description="进货单价")


class PurchaseItemCreate(PurchaseItemBase):
    """创建进货明细模型"""
    pass


class PurchaseItemResponse(PurchaseItemBase):
    """进货明细响应模型"""
    id: int
    purchase_id: int
    total_price: Decimal = Field(..., description="小计金额")
    created_at: datetime
    product_name: Optional[str] = None  # 商品名称（关联查询）

    class Config:
        from_attributes = True

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)


class PurchaseBase(BaseModel):
    """进货单基础模型"""
    supplier_id: int = Field(..., description="供货商ID")
    purchase_date: date = Field(..., description="进货日期")
    notes: Optional[str] = Field(None, description="备注", max_length=500)


class PurchaseCreate(PurchaseBase):
    """创建进货单模型"""
    items: List[PurchaseItemCreate] = Field(..., min_items=1, description="进货明细列表")


class PurchaseUpdate(BaseModel):
    """更新进货单模型（通常不允许更新，但保留接口）"""
    purchase_date: Optional[date] = Field(None, description="进货日期")
    notes: Optional[str] = Field(None, description="备注", max_length=500)


class PurchaseResponse(PurchaseBase):
    """进货单响应模型"""
    id: int
    total_amount: Decimal = Field(..., description="总金额")
    created_at: datetime
    updated_at: datetime
    supplier_name: Optional[str] = None  # 供货商名称（关联查询）
    items: List[PurchaseItemResponse] = []  # 进货明细列表

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)


