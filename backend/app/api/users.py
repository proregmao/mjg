"""
用户管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import bcrypt
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserBatchDelete
)

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # bcrypt限制密码长度不能超过72字节，需要截断
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    # 使用bcrypt直接加密
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # bcrypt限制密码长度不能超过72字节，需要截断
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


@router.get("", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    query = db.query(User)
    
    # 默认不显示已删除的用户
    query = query.filter(or_(User.deleted_at == None, User.deleted_at.is_(None)))
    
    if search:
        query = query.filter(
            or_(
                User.username.like(f"%{search}%"),
                User.email.like(f"%{search}%")
            )
        )
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.deleted_at:
        raise HTTPException(status_code=404, detail="用户已删除")
    return user


@router.post("", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建用户"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已存在")
    
    # 创建新用户
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
        is_verified=user.is_verified
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """更新用户"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if db_user.deleted_at:
        raise HTTPException(status_code=404, detail="用户已删除")
    
    # 检查邮箱是否被其他用户使用
    if user_update.email and user_update.email != db_user.email:
        existing_email = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被其他用户使用")
    
    # 更新字段
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户（软删除）"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if db_user.deleted_at:
        raise HTTPException(status_code=400, detail="用户已删除")
    
    # 软删除：设置删除时间
    from datetime import datetime, timezone
    db_user.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "用户删除成功"}


@router.post("/batch-delete")
def batch_delete_users(
    batch_delete: UserBatchDelete,
    db: Session = Depends(get_db)
):
    """批量删除用户（软删除）"""
    if not batch_delete.ids:
        raise HTTPException(status_code=400, detail="请提供要删除的用户ID列表")
    
    users = db.query(User).filter(
        User.id.in_(batch_delete.ids),
        User.deleted_at.is_(None)
    ).all()
    
    if not users:
        raise HTTPException(status_code=404, detail="未找到要删除的用户")
    
    # 软删除：设置删除时间
    from datetime import datetime, timezone
    delete_time = datetime.now(timezone.utc)
    for user in users:
        user.deleted_at = delete_time
    
    db.commit()
    return {"message": f"成功删除 {len(users)} 个用户", "deleted_count": len(users)}

