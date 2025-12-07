"""
认证相关API
"""
from fastapi import APIRouter, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import Optional
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="", tags=["认证"])  # 不使用/api前缀，因为前端直接调用/login
security = HTTPBearer()

# 简单的token存储（生产环境应使用Redis或数据库）
tokens = {}


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    accessToken: str = Field(..., description="访问令牌")
    username: str = Field(..., description="用户名")


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    username: str
    avatar: Optional[str] = None
    permissions: list = []


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录
    注意：这是简化版本，内部系统不需要复杂认证
    任意用户名和密码都可以登录
    """
    # 简化认证：任意用户名和密码都可以登录
    # 生产环境应该验证用户名和密码
    
    # 生成token
    token = secrets.token_urlsafe(32)
    tokens[token] = {
        "username": request.username,
        "created_at": datetime.now()
    }
    
    return LoginResponse(
        accessToken=token,
        username=request.username
    )


class UserInfoRequest(BaseModel):
    """用户信息请求"""
    accessToken: Optional[str] = None


@router.post("/userInfo", response_model=UserInfoResponse)
async def get_user_info(request: UserInfoRequest = None):
    """
    获取用户信息
    """
    # 简化版本：直接返回默认用户信息
    # 内部系统不需要复杂的token验证
    token = request.accessToken if request else None
    
    if token and token in tokens:
        user_data = tokens[token]
        return UserInfoResponse(
            username=user_data["username"],
            avatar=None,
            permissions=["admin"]  # 默认管理员权限
        )
    else:
        # 如果没有token或token无效，返回默认用户信息
        return UserInfoResponse(
            username="admin",
            avatar=None,
            permissions=["admin"]
        )


class LogoutRequest(BaseModel):
    """退出登录请求"""
    token: Optional[str] = None


@router.post("/logout")
async def logout(request: LogoutRequest = None):
    """
    退出登录
    """
    token = request.token if request else None
    if token and token in tokens:
        del tokens[token]
    return {"message": "退出成功"}


@router.post("/register")
async def register(request: LoginRequest):
    """
    用户注册（简化版本，直接返回登录成功）
    """
    # 简化版本：直接登录
    token = secrets.token_urlsafe(32)
    tokens[token] = {
        "username": request.username,
        "created_at": datetime.now()
    }
    
    return LoginResponse(
        accessToken=token,
        username=request.username
    )

