"""
其它收入管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from app.db.database import get_db
from app.models.other_income import OtherIncome
from app.schemas.other_income import (
    OtherIncomeCreate, OtherIncomeUpdate, OtherIncomeResponse
)

router = APIRouter(prefix="/api/other-incomes", tags=["其它收入管理"])


@router.get("", response_model=List[OtherIncomeResponse])
def get_other_incomes(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取其它收入列表"""
    query = db.query(OtherIncome)
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(OtherIncome.income_date >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(OtherIncome.income_date <= end_datetime)
    
    incomes = query.order_by(OtherIncome.income_date.desc(), OtherIncome.created_at.desc()).offset(skip).limit(limit).all()
    return incomes


@router.get("/{income_id}", response_model=OtherIncomeResponse)
def get_other_income(income_id: int, db: Session = Depends(get_db)):
    """获取其它收入详情"""
    income = db.query(OtherIncome).filter(OtherIncome.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="收入记录不存在")
    return income


@router.post("", response_model=OtherIncomeResponse)
def create_other_income(income: OtherIncomeCreate, db: Session = Depends(get_db)):
    """创建其它收入"""
    db_income = OtherIncome(
        name=income.name,
        amount=income.amount,
        payment_method=income.payment_method or "现金",
        description=income.description,
        income_date=income.income_date
    )
    db.add(db_income)
    db.commit()
    db.refresh(db_income)
    return db_income


@router.put("/{income_id}", response_model=OtherIncomeResponse)
def update_other_income(
    income_id: int,
    income: OtherIncomeUpdate,
    db: Session = Depends(get_db)
):
    """更新其它收入"""
    db_income = db.query(OtherIncome).filter(OtherIncome.id == income_id).first()
    if not db_income:
        raise HTTPException(status_code=404, detail="收入记录不存在")
    
    if income.name is not None:
        db_income.name = income.name
    if income.amount is not None:
        db_income.amount = income.amount
    if income.payment_method is not None:
        db_income.payment_method = income.payment_method
    if income.description is not None:
        db_income.description = income.description
    if income.income_date is not None:
        db_income.income_date = income.income_date
    
    db.commit()
    db.refresh(db_income)
    return db_income


@router.delete("/{income_id}")
def delete_other_income(income_id: int, db: Session = Depends(get_db)):
    """删除其它收入"""
    income = db.query(OtherIncome).filter(OtherIncome.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="收入记录不存在")
    
    db.delete(income)
    db.commit()
    return {"message": "收入记录已删除"}


