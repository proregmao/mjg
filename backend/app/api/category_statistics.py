"""
分类统计API（房间收入/支出、其它收入/支出）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.db.database import get_db
from app.models.room_session import RoomSession
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord
from app.models.other_expense import OtherExpense
from app.models.other_income import OtherIncome
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/category-statistics", tags=["分类统计"])


class CategoryStatisticsResponse(BaseModel):
    """分类统计响应模型"""
    date_range: str = Field(..., description="日期范围")
    room_income: Decimal = Field(default=0, description="房间收入总额")
    room_expense: Decimal = Field(default=0, description="房间支出总额（成本）")
    room_profit: Decimal = Field(default=0, description="房间利润")
    other_income: Decimal = Field(default=0, description="其它收入总额")
    other_expense: Decimal = Field(default=0, description="其它支出总额")
    total_income: Decimal = Field(default=0, description="总收入（房间收入+其它收入）")
    total_expense: Decimal = Field(default=0, description="总支出（房间成本+其它支出）")
    total_profit: Decimal = Field(default=0, description="总利润")
    room_income_details: dict = Field(default_factory=dict, description="房间收入明细")
    room_expense_details: dict = Field(default_factory=dict, description="房间支出明细")
    other_income_list: list = Field(default_factory=list, description="其它收入列表")
    other_expense_list: list = Field(default_factory=list, description="其它支出列表")


@router.get("", response_model=CategoryStatisticsResponse)
def get_category_statistics(
    start_date: Optional[date] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取分类统计
    支持按日期范围统计，如果不提供日期则统计所有数据
    """
    # 初始化统计
    room_income = Decimal("0")
    room_expense = Decimal("0")
    other_income = Decimal("0")
    other_expense = Decimal("0")
    
    room_income_details = {
        "table_fee": Decimal("0"),  # 台子费
        "product_revenue": Decimal("0"),  # 商品收入
        "meal_revenue": Decimal("0")  # 餐费收入
    }
    
    room_expense_details = {
        "product_cost": Decimal("0"),  # 商品成本
        "meal_cost": Decimal("0")  # 餐费成本
    }
    
    other_income_list = []
    other_expense_list = []
    
    # 构建日期过滤条件
    start_datetime = None
    end_datetime = None
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # 统计房间收入（台子费、商品、餐费）
    sessions_query = db.query(RoomSession).filter(RoomSession.status == "settled")
    if start_datetime:
        sessions_query = sessions_query.filter(RoomSession.start_time >= start_datetime)
    if end_datetime:
        sessions_query = sessions_query.filter(RoomSession.start_time <= end_datetime)
    sessions = sessions_query.all()
    
    for session in sessions:
        # 台子费
        table_fee = session.table_fee or Decimal("0")
        room_income += table_fee
        room_income_details["table_fee"] += table_fee
        
        # 商品消费
        consumptions = db.query(ProductConsumption).filter(ProductConsumption.session_id == session.id).all()
        for consumption in consumptions:
            product_revenue = consumption.total_price or Decimal("0")
            product_cost = consumption.total_cost or Decimal("0")
            room_income += product_revenue
            room_expense += product_cost
            room_income_details["product_revenue"] += product_revenue
            room_expense_details["product_cost"] += product_cost
        
        # 餐费
        meals = db.query(MealRecord).filter(MealRecord.session_id == session.id).all()
        for meal in meals:
            meal_revenue = meal.amount or Decimal("0")
            meal_cost = meal.cost_price or Decimal("0")
            room_income += meal_revenue
            room_expense += meal_cost
            room_income_details["meal_revenue"] += meal_revenue
            room_expense_details["meal_cost"] += meal_cost
    
    # 统计其它收入
    other_incomes_query = db.query(OtherIncome)
    if start_datetime:
        other_incomes_query = other_incomes_query.filter(OtherIncome.income_date >= start_datetime)
    if end_datetime:
        other_incomes_query = other_incomes_query.filter(OtherIncome.income_date <= end_datetime)
    other_incomes = other_incomes_query.order_by(OtherIncome.income_date.desc()).all()
    
    for income in other_incomes:
        amount = income.amount or Decimal("0")
        other_income += amount
        other_income_list.append({
            "id": income.id,
            "name": income.name,
            "amount": float(amount),
            "payment_method": income.payment_method or "现金",
            "description": income.description,
            "income_date": income.income_date.strftime("%Y-%m-%d %H:%M:%S") if income.income_date else ""
        })
    
    # 统计其它支出
    other_expenses_query = db.query(OtherExpense)
    if start_datetime:
        other_expenses_query = other_expenses_query.filter(OtherExpense.expense_date >= start_datetime)
    if end_datetime:
        other_expenses_query = other_expenses_query.filter(OtherExpense.expense_date <= end_datetime)
    other_expenses = other_expenses_query.order_by(OtherExpense.expense_date.desc()).all()
    
    for expense in other_expenses:
        amount = expense.amount or Decimal("0")
        other_expense += amount
        other_expense_list.append({
            "id": expense.id,
            "name": expense.name,
            "amount": float(amount),
            "payment_method": expense.payment_method or "现金",
            "description": expense.description,
            "expense_date": expense.expense_date.strftime("%Y-%m-%d %H:%M:%S") if expense.expense_date else ""
        })
    
    # 计算利润
    room_profit = room_income - room_expense
    total_income = room_income + other_income
    total_expense = room_expense + other_expense
    total_profit = total_income - total_expense
    
    # 格式化日期范围
    if start_date and end_date:
        date_range = f"{start_date} 至 {end_date}"
    elif start_date:
        date_range = f"{start_date} 起"
    elif end_date:
        date_range = f"至 {end_date}"
    else:
        date_range = "全部"
    
    # 转换明细为float（用于JSON序列化）
    def convert_details(details):
        return {k: float(v) for k, v in details.items()}
    
    return CategoryStatisticsResponse(
        date_range=date_range,
        room_income=room_income,
        room_expense=room_expense,
        room_profit=room_profit,
        other_income=other_income,
        other_expense=other_expense,
        total_income=total_income,
        total_expense=total_expense,
        total_profit=total_profit,
        room_income_details=convert_details(room_income_details),
        room_expense_details=convert_details(room_expense_details),
        other_income_list=other_income_list,
        other_expense_list=other_expense_list
    )











