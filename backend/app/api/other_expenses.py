"""
其它支出管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from app.db.database import get_db
from app.models.other_expense import OtherExpense
from app.schemas.other_expense import (
    OtherExpenseCreate, OtherExpenseUpdate, OtherExpenseResponse
)

router = APIRouter(prefix="/api/other-expenses", tags=["其它支出管理"])


@router.get("", response_model=List[OtherExpenseResponse])
def get_other_expenses(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取其它支出列表"""
    query = db.query(OtherExpense)
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(OtherExpense.expense_date >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(OtherExpense.expense_date <= end_datetime)
    
    expenses = query.order_by(OtherExpense.expense_date.desc(), OtherExpense.created_at.desc()).offset(skip).limit(limit).all()
    return expenses


@router.get("/{expense_id}", response_model=OtherExpenseResponse)
def get_other_expense(expense_id: int, db: Session = Depends(get_db)):
    """获取其它支出详情"""
    expense = db.query(OtherExpense).filter(OtherExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="支出记录不存在")
    return expense


@router.post("", response_model=OtherExpenseResponse)
def create_other_expense(expense: OtherExpenseCreate, db: Session = Depends(get_db)):
    """创建其它支出"""
    db_expense = OtherExpense(
        name=expense.name,
        amount=expense.amount,
        payment_method=expense.payment_method or "现金",
        description=expense.description,
        expense_date=expense.expense_date
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


@router.put("/{expense_id}", response_model=OtherExpenseResponse)
def update_other_expense(
    expense_id: int,
    expense: OtherExpenseUpdate,
    db: Session = Depends(get_db)
):
    """更新其它支出"""
    db_expense = db.query(OtherExpense).filter(OtherExpense.id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="支出记录不存在")
    
    if expense.name is not None:
        db_expense.name = expense.name
    if expense.amount is not None:
        db_expense.amount = expense.amount
    if expense.payment_method is not None:
        db_expense.payment_method = expense.payment_method
    if expense.description is not None:
        db_expense.description = expense.description
    if expense.expense_date is not None:
        db_expense.expense_date = expense.expense_date
    
    db.commit()
    db.refresh(db_expense)
    return db_expense


@router.delete("/{expense_id}")
def delete_other_expense(expense_id: int, db: Session = Depends(get_db)):
    """删除其它支出"""
    expense = db.query(OtherExpense).filter(OtherExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="支出记录不存在")
    
    db.delete(expense)
    db.commit()
    return {"message": "支出记录已删除"}


