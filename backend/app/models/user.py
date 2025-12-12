"""
用户模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True, comment="用户名")
    email = Column(String(255), nullable=False, unique=True, index=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), default="user", comment="角色：admin=管理员, user=普通用户")
    is_verified = Column(Boolean, default=True, comment="是否已激活")
    email_verified_at = Column(DateTime(timezone=True), nullable=True, comment="邮箱验证时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="删除时间")

    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
    )


