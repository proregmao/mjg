"""
房间相关的Pydantic模型
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


class RoomBase(BaseModel):
    """房间基础模型"""
    name: str = Field(..., description="名称", max_length=100)


class RoomCreate(RoomBase):
    """创建房间模型"""
    pass


class RoomUpdate(BaseModel):
    """更新房间模型"""
    name: Optional[str] = Field(None, description="名称", max_length=100)


class RoomResponse(RoomBase):
    """房间响应模型"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)


class RoomSessionResponse(BaseModel):
    """房间使用记录响应模型"""
    id: int
    room_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    table_fee: Decimal
    total_revenue: Decimal
    total_cost: Decimal
    total_profit: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('start_time', 'end_time', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)


class StartSessionRequest(BaseModel):
    """开始使用房间请求"""
    room_id: int = Field(..., description="房间ID")


class AddCustomerRequest(BaseModel):
    """添加客户到房间请求"""
    customer_id: int = Field(..., description="客户ID")


class RecordLoanRequest(BaseModel):
    """记录借款请求"""
    customer_id: int = Field(..., description="客户ID")
    amount: Decimal = Field(..., gt=0, description="借款金额")
    payment_method: Optional[str] = Field("现金", description="支付方式：现金、微信、支付宝、转账，默认为现金")


class RecordRepaymentRequest(BaseModel):
    """记录还款请求"""
    loan_id: Optional[int] = Field(None, description="借款记录ID（可选，如果有则还此笔借款，否则直接冲抵总欠款）")
    customer_id: int = Field(..., description="客户ID")
    amount: Decimal = Field(..., ne=0, description="还款金额（正数为还款，负数为退款/支付，可超过借款金额，超出部分冲抵总欠款）")
    payment_method: Optional[str] = Field("现金", description="还款方式：现金、微信、支付宝、转账，默认为现金")


class RecordProductRequest(BaseModel):
    """记录商品消费请求"""
    product_id: int = Field(..., description="商品ID")
    customer_id: Optional[int] = Field(None, description="客户ID（可选）")
    quantity: int = Field(..., gt=0, description="数量")
    payment_method: Optional[str] = Field("现金", description="支付方式：现金、微信、支付宝、转账，默认为现金")


class RecordMealRequest(BaseModel):
    """记录餐费请求"""
    product_id: int = Field(..., description="餐费商品ID")
    customer_id: Optional[int] = Field(None, description="客户ID（可选）")
    amount: Decimal = Field(..., gt=0, description="餐费金额")
    payment_method: Optional[str] = Field("现金", description="支付方式：现金、微信、支付宝、转账，默认为现金")
    description: Optional[str] = Field(None, description="餐费说明")


class TransferRoomRequest(BaseModel):
    """房间转移请求"""
    to_room_id: int = Field(..., description="目标房间ID")


class SetTableFeeRequest(BaseModel):
    """设置台子费请求"""
    table_fee: Decimal = Field(..., ge=0, description="台子费")
    payment_method: Optional[str] = Field("现金", description="支付方式：现金、微信、支付宝、转账，默认为现金")


class UpdateProductConsumptionRequest(BaseModel):
    """更新商品消费请求"""
    quantity: int = Field(..., gt=0, description="数量")


class UpdateMealRecordRequest(BaseModel):
    """更新餐费记录请求"""
    amount: Decimal = Field(..., gt=0, description="餐费金额")









