"""
用户相关的Pydantic模型
"""
from pydantic import BaseModel, Field, EmailStr, field_serializer
from typing import Optional
from datetime import datetime, timezone, timedelta

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


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., description="用户名", max_length=100)
    email: EmailStr = Field(..., description="邮箱")
    role: str = Field("user", description="角色：admin=管理员, user=普通用户")
    is_verified: bool = Field(True, description="是否已激活")


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., description="密码", min_length=6)


class UserUpdate(BaseModel):
    """更新用户模型"""
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: Optional[str] = Field(None, description="密码", min_length=6)
    role: Optional[str] = Field(None, description="角色：admin=管理员, user=普通用户")
    is_verified: Optional[bool] = Field(None, description="是否已激活")


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    email_verified_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at', 'email_verified_at', 'deleted_at')
    def serialize_datetime(self, dt: datetime) -> Optional[str]:
        if dt is None:
            return None
        return format_datetime_local(dt)


class UserBatchDelete(BaseModel):
    """批量删除用户模型"""
    ids: list[int] = Field(..., description="要删除的用户ID列表")

