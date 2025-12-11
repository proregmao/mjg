"""
操作日志API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime, date
from app.db.database import get_db
from app.models.operation_log import OperationLog
from pydantic import BaseModel, Field
from decimal import Decimal

router = APIRouter(prefix="/api/operation-logs", tags=["操作日志"])


class OperationLogResponse(BaseModel):
    """操作日志响应模型"""
    id: int
    user_id: Optional[int] = None
    username: str
    action: str
    module: str
    method: str
    path: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_data: Optional[str] = None
    response_data: Optional[str] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    execution_time: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[OperationLogResponse])
def get_operation_logs(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=1000, description="返回记录数"),
    username: Optional[str] = Query(None, description="用户名筛选"),
    action: Optional[str] = Query(None, description="操作类型筛选"),
    module: Optional[str] = Query(None, description="模块筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取操作日志列表"""
    query = db.query(OperationLog)
    
    # 用户名筛选
    if username:
        query = query.filter(OperationLog.username.like(f"%{username}%"))
    
    # 操作类型筛选
    if action:
        query = query.filter(OperationLog.action.like(f"%{action}%"))
    
    # 模块筛选
    if module:
        query = query.filter(OperationLog.module.like(f"%{module}%"))
    
    # 日期范围筛选
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(OperationLog.created_at >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(OperationLog.created_at <= end_datetime)
    
    # 按创建时间倒序排列
    logs = query.order_by(desc(OperationLog.created_at)).offset(skip).limit(limit).all()
    return logs


@router.get("/{log_id}", response_model=OperationLogResponse)
def get_operation_log(log_id: int, db: Session = Depends(get_db)):
    """获取操作日志详情"""
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="操作日志不存在")
    return log


@router.delete("/{log_id}")
def delete_operation_log(log_id: int, db: Session = Depends(get_db)):
    """删除操作日志"""
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="操作日志不存在")
    
    db.delete(log)
    db.commit()
    return {"message": "操作日志已删除"}


@router.delete("")
def clear_operation_logs(
    days: int = Query(30, ge=1, le=365, description="保留最近N天的日志"),
    db: Session = Depends(get_db)
):
    """清理操作日志（保留最近N天的日志）"""
    from datetime import timedelta
    cutoff_date = datetime.now() - timedelta(days=days)
    
    deleted_count = db.query(OperationLog).filter(
        OperationLog.created_at < cutoff_date
    ).delete()
    
    db.commit()
    return {"message": f"已删除 {deleted_count} 条操作日志"}








