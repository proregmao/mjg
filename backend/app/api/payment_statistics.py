"""
支付方式统计API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.db.database import get_db
from app.models.room_session import RoomSession
from app.models.customer_loan import CustomerLoan
from app.models.customer_repayment import CustomerRepayment
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord
from app.models.other_expense import OtherExpense
from app.models.other_income import OtherIncome
from app.models.system_config import SystemConfig
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/payment-statistics", tags=["支付方式统计"])


class PaymentMethodStatisticsResponse(BaseModel):
    """支付方式统计响应模型"""
    date_range: str = Field(..., description="日期范围")
    initial_cash: Decimal = Field(default=0, description="初期现金")
    cash_total: Decimal = Field(default=0, description="现金总额")
    wechat_total: Decimal = Field(default=0, description="微信总额")
    alipay_total: Decimal = Field(default=0, description="支付宝总额")
    transfer_total: Decimal = Field(default=0, description="转账总额")
    cash_breakdown: dict = Field(default_factory=dict, description="现金明细")
    wechat_breakdown: dict = Field(default_factory=dict, description="微信明细")
    alipay_breakdown: dict = Field(default_factory=dict, description="支付宝明细")
    transfer_breakdown: dict = Field(default_factory=dict, description="转账明细")


@router.get("", response_model=PaymentMethodStatisticsResponse)
def get_payment_statistics(
    start_date: Optional[date] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取支付方式统计
    支持按日期范围统计，如果不提供日期则统计所有数据
    """
    # 获取初期现金
    initial_cash_config = db.query(SystemConfig).filter(SystemConfig.key == "initial_cash").first()
    initial_cash = Decimal(initial_cash_config.value) if initial_cash_config else Decimal("0")
    
    # 初始化统计
    cash_total = initial_cash
    wechat_total = Decimal("0")
    alipay_total = Decimal("0")
    transfer_total = Decimal("0")
    
    cash_breakdown = {
        "loans": Decimal("0"),  # 借款（减少现金）
        "repayments": Decimal("0"),  # 还款（增加现金）
        "room_income": Decimal("0"),  # 房间收入（增加现金）
        "other_income": Decimal("0"),  # 其它收入（增加现金）
        "other_expense": Decimal("0")  # 其它支出（减少现金）
    }
    
    wechat_breakdown = {
        "loans": Decimal("0"),
        "repayments": Decimal("0"),
        "room_income": Decimal("0"),
        "other_income": Decimal("0"),
        "other_expense": Decimal("0")
    }
    
    alipay_breakdown = {
        "loans": Decimal("0"),
        "repayments": Decimal("0"),
        "room_income": Decimal("0"),
        "other_income": Decimal("0"),
        "other_expense": Decimal("0")
    }
    
    transfer_breakdown = {
        "loans": Decimal("0"),
        "repayments": Decimal("0"),
        "room_income": Decimal("0"),
        "other_income": Decimal("0"),
        "other_expense": Decimal("0")
    }
    
    # 构建日期过滤条件
    date_filter = None
    if start_date and end_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        date_filter = lambda dt: start_datetime <= dt <= end_datetime
    elif start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        date_filter = lambda dt: dt >= start_datetime
    elif end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        date_filter = lambda dt: dt <= end_datetime
    
    # 统计借款（减少现金/微信/支付宝）
    loans_query = db.query(CustomerLoan)
    if date_filter:
        loans_query = loans_query.filter(CustomerLoan.created_at >= start_datetime if start_date else True,
                                        CustomerLoan.created_at <= end_datetime if end_date else True)
    loans = loans_query.all()
    
    for loan in loans:
        if date_filter and not date_filter(loan.created_at):
            continue
        method = loan.payment_method or "现金"
        amount = loan.amount or Decimal("0")
        if method == "现金":
            cash_total -= amount
            cash_breakdown["loans"] += amount
        elif method == "微信":
            wechat_total -= amount
            wechat_breakdown["loans"] += amount
        elif method == "支付宝":
            alipay_total -= amount
            alipay_breakdown["loans"] += amount
        elif method == "转账":
            transfer_total -= amount
            transfer_breakdown["loans"] += amount
    
    # 统计还款（增加现金/微信/支付宝）
    if date_filter:
        repayments_query = db.query(CustomerRepayment)
        if start_datetime:
            repayments_query = repayments_query.filter(CustomerRepayment.created_at >= start_datetime)
        if end_datetime:
            repayments_query = repayments_query.filter(CustomerRepayment.created_at <= end_datetime)
        repayments = repayments_query.all()
    else:
        repayments = db.query(CustomerRepayment).all()
    
    for repayment in repayments:
        if date_filter and not date_filter(repayment.created_at):
            continue
        method = repayment.payment_method or "现金"
        amount = repayment.amount or Decimal("0")
        if method == "现金":
            cash_total += amount
            cash_breakdown["repayments"] += amount
        elif method == "微信":
            wechat_total += amount
            wechat_breakdown["repayments"] += amount
        elif method == "支付宝":
            alipay_total += amount
            alipay_breakdown["repayments"] += amount
        elif method == "转账":
            transfer_total += amount
            transfer_breakdown["repayments"] += amount
    
    # 统计房间收入（台子费、商品、餐费）
    sessions_query = db.query(RoomSession).filter(RoomSession.status == "settled")
    if date_filter:
        if start_datetime:
            sessions_query = sessions_query.filter(RoomSession.start_time >= start_datetime)
        if end_datetime:
            sessions_query = sessions_query.filter(RoomSession.start_time <= end_datetime)
    sessions = sessions_query.all()
    
    for session in sessions:
        if date_filter and not date_filter(session.start_time):
            continue
        
        # 台子费
        table_fee = session.table_fee or Decimal("0")
        method = session.table_fee_payment_method or "现金"
        if method == "现金":
            cash_total += table_fee
            cash_breakdown["room_income"] += table_fee
        elif method == "微信":
            wechat_total += table_fee
            wechat_breakdown["room_income"] += table_fee
        elif method == "支付宝":
            alipay_total += table_fee
            alipay_breakdown["room_income"] += table_fee
        elif method == "转账":
            transfer_total += table_fee
            transfer_breakdown["room_income"] += table_fee
        
        # 商品消费
        consumptions = db.query(ProductConsumption).filter(ProductConsumption.session_id == session.id).all()
        for consumption in consumptions:
            amount = consumption.total_price or Decimal("0")
            method = consumption.payment_method or "现金"
            if method == "现金":
                cash_total += amount
                cash_breakdown["room_income"] += amount
            elif method == "微信":
                wechat_total += amount
                wechat_breakdown["room_income"] += amount
            elif method == "支付宝":
                alipay_total += amount
                alipay_breakdown["room_income"] += amount
            elif method == "转账":
                transfer_total += amount
                transfer_breakdown["room_income"] += amount
        
        # 餐费
        meals = db.query(MealRecord).filter(MealRecord.session_id == session.id).all()
        for meal in meals:
            amount = meal.amount or Decimal("0")
            method = meal.payment_method or "现金"
            if method == "现金":
                cash_total += amount
                cash_breakdown["room_income"] += amount
            elif method == "微信":
                wechat_total += amount
                wechat_breakdown["room_income"] += amount
            elif method == "支付宝":
                alipay_total += amount
                alipay_breakdown["room_income"] += amount
            elif method == "转账":
                transfer_total += amount
                transfer_breakdown["room_income"] += amount
    
    # 统计其它收入
    if date_filter:
        other_incomes_query = db.query(OtherIncome)
        if start_datetime:
            other_incomes_query = other_incomes_query.filter(OtherIncome.income_date >= start_datetime)
        if end_datetime:
            other_incomes_query = other_incomes_query.filter(OtherIncome.income_date <= end_datetime)
        other_incomes = other_incomes_query.all()
    else:
        other_incomes = db.query(OtherIncome).all()
    
    for income in other_incomes:
        if date_filter and not date_filter(income.income_date):
            continue
        method = income.payment_method or "现金"
        amount = income.amount or Decimal("0")
        if method == "现金":
            cash_total += amount
            cash_breakdown["other_income"] += amount
        elif method == "微信":
            wechat_total += amount
            wechat_breakdown["other_income"] += amount
        elif method == "支付宝":
            alipay_total += amount
            alipay_breakdown["other_income"] += amount
        elif method == "转账":
            transfer_total += amount
            transfer_breakdown["other_income"] += amount
    
    # 统计其它支出
    if date_filter:
        other_expenses_query = db.query(OtherExpense)
        if start_datetime:
            other_expenses_query = other_expenses_query.filter(OtherExpense.expense_date >= start_datetime)
        if end_datetime:
            other_expenses_query = other_expenses_query.filter(OtherExpense.expense_date <= end_datetime)
        other_expenses = other_expenses_query.all()
    else:
        other_expenses = db.query(OtherExpense).all()
    
    for expense in other_expenses:
        if date_filter and not date_filter(expense.expense_date):
            continue
        method = expense.payment_method or "现金"
        amount = expense.amount or Decimal("0")
        if method == "现金":
            cash_total -= amount
            cash_breakdown["other_expense"] += amount
        elif method == "微信":
            wechat_total -= amount
            wechat_breakdown["other_expense"] += amount
        elif method == "支付宝":
            alipay_total -= amount
            alipay_breakdown["other_expense"] += amount
        elif method == "转账":
            transfer_total -= amount
            transfer_breakdown["other_expense"] += amount
    
    # 格式化日期范围
    if start_date and end_date:
        date_range = f"{start_date} 至 {end_date}"
    elif start_date:
        date_range = f"{start_date} 起"
    elif end_date:
        date_range = f"至 {end_date}"
    else:
        date_range = "全部"
    
    # 转换breakdown为float（用于JSON序列化）
    def convert_breakdown(bd):
        return {k: float(v) for k, v in bd.items()}
    
    return PaymentMethodStatisticsResponse(
        date_range=date_range,
        initial_cash=initial_cash,
        cash_total=cash_total,
        wechat_total=wechat_total,
        alipay_total=alipay_total,
        transfer_total=transfer_total,
        cash_breakdown=convert_breakdown(cash_breakdown),
        wechat_breakdown=convert_breakdown(wechat_breakdown),
        alipay_breakdown=convert_breakdown(alipay_breakdown),
        transfer_breakdown=convert_breakdown(transfer_breakdown)
    )

