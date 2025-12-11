"""
房间使用记录详情相关的Pydantic模型
"""
from pydantic import BaseModel, Field, field_serializer, ConfigDict
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


class RoomCustomerDetail(BaseModel):
    """房间客户详情"""
    id: int
    customer_id: int
    customer_name: str
    customer_phone: Optional[str] = None
    joined_at: datetime
    left_at: Optional[datetime] = None

    @field_serializer('joined_at', 'left_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)


class LoanDetail(BaseModel):
    """借款记录详情"""
    id: int
    customer_id: int
    customer_name: str
    amount: Decimal
    remaining_amount: Decimal
    payment_method: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)


class RepaymentDetail(BaseModel):
    """还款记录详情"""
    id: int
    customer_id: int
    customer_name: str
    loan_id: Optional[int] = None
    amount: Decimal
    payment_method: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)


class ProductConsumptionDetail(BaseModel):
    """商品消费详情"""
    id: int
    product_id: int
    product_name: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    payment_method: Optional[str] = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)


class MealRecordDetail(BaseModel):
    """餐费记录详情"""
    id: int
    product_id: int
    product_name: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    amount: Decimal
    description: Optional[str] = None
    payment_method: Optional[str] = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return format_datetime_local(dt)


class RoomSessionDetailResponse(BaseModel):
    """房间使用记录详情响应模型"""
    # Pydantic v2 配置
    model_config = ConfigDict(
        # 确保空列表也会被序列化
        exclude_none=False,
        exclude_unset=False,
    )
    
    id: int
    room_id: int
    room_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    table_fee: Decimal
    table_fee_payment_method: Optional[str] = Field(default=None, exclude=False)
    total_revenue: Decimal
    total_cost: Decimal
    total_profit: Decimal
    created_at: datetime
    updated_at: datetime
    customers: List[RoomCustomerDetail] = Field(default_factory=list)
    loans: List[LoanDetail] = Field(default_factory=list)
    repayments: List[RepaymentDetail] = Field(default_factory=list)
    product_consumptions: List[ProductConsumptionDetail] = Field(default_factory=list)
    meal_records: List[MealRecordDetail] = Field(default_factory=list)

    @field_serializer('start_time', 'end_time', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)









