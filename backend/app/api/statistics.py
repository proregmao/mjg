"""
统计报表API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from sqlalchemy.sql import func as sql_func
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.db.database import get_db
from app.models.room_session import RoomSession
from app.models.customer import Customer
from app.models.customer_loan import CustomerLoan
from app.models.customer_repayment import CustomerRepayment
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord
from app.models.room import Room
from app.models.product import Product
from app.models.other_expense import OtherExpense
from app.models.other_income import OtherIncome
from app.schemas.statistics import (
    DailyStatisticsResponse, MonthlyStatisticsResponse,
    CustomerRankingItem, RoomUsageItem, ProductSalesItem,
    RoomDetailItem, CostDetailItem, CustomerFinancialItem
)

router = APIRouter(prefix="/api/statistics", tags=["统计报表"])


@router.get("/daily", response_model=DailyStatisticsResponse)
def get_daily_statistics(
    target_date: Optional[date] = Query(None, alias="date", description="日期，格式：YYYY-MM-DD，不填则使用今天"),
    db: Session = Depends(get_db)
):
    """获取每日统计"""
    if target_date is None:
        target_date = date.today()
    
    # 查询当天的房间使用记录
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    sessions = db.query(RoomSession).filter(
        and_(
            RoomSession.start_time >= start_datetime,
            RoomSession.start_time <= end_datetime,
            RoomSession.status == "settled"
        )
    ).all()
    
    # 计算统计数据
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    table_fee_total = Decimal("0")
    product_revenue = Decimal("0")
    product_cost = Decimal("0")
    meal_revenue = Decimal("0")
    meal_cost = Decimal("0")
    room_ids = set()
    
    # 房间详情字典 {room_id: {name, table_fee, session_count}}
    room_details_dict = {}
    
    for session in sessions:
        total_revenue += session.total_revenue or Decimal("0")
        total_cost += session.total_cost or Decimal("0")
        table_fee = session.table_fee or Decimal("0")
        table_fee_total += table_fee
        room_ids.add(session.room_id)
        
        # 统计房间详情
        if session.room_id not in room_details_dict:
            room = db.query(Room).filter(Room.id == session.room_id).first()
            room_details_dict[session.room_id] = {
                "room_id": session.room_id,
                "room_name": room.name if room else f"房间{session.room_id}",
                "table_fee": Decimal("0"),
                "session_count": 0
            }
        room_details_dict[session.room_id]["table_fee"] += table_fee
        room_details_dict[session.room_id]["session_count"] += 1
        
        # 查询商品消费
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session.id
        ).all()
        for consumption in consumptions:
            product_revenue += consumption.total_price or Decimal("0")
            product_cost += consumption.total_cost or Decimal("0")
        
        # 查询餐费
        meals = db.query(MealRecord).filter(
            MealRecord.session_id == session.id
        ).all()
        for meal in meals:
            meal_revenue += meal.amount or Decimal("0")
            meal_cost += meal.cost_price or Decimal("0")
    
    # 查询当天的其它支出和收入
    other_expenses = db.query(OtherExpense).filter(
        and_(
            OtherExpense.expense_date >= start_datetime,
            OtherExpense.expense_date <= end_datetime
        )
    ).all()
    
    other_incomes = db.query(OtherIncome).filter(
        and_(
            OtherIncome.income_date >= start_datetime,
            OtherIncome.income_date <= end_datetime
        )
    ).all()
    
    other_expense_total = sum(exp.amount for exp in other_expenses)
    other_income_total = sum(inc.amount for inc in other_incomes)
    
    # 利润 = 房间收入 - 房间成本 + 其它收入 - 其它支出
    total_profit = table_fee_total - product_cost - meal_cost + other_income_total - other_expense_total
    
    # 构建房间详情列表
    room_details = [
        RoomDetailItem(
            room_id=room_id,
            room_name=details["room_name"],
            table_fee=details["table_fee"],
            session_count=details["session_count"]
        )
        for room_id, details in room_details_dict.items()
    ]
    
    # 构建成本明细列表
    cost_details = []
    if product_cost > 0:
        cost_details.append(CostDetailItem(
            cost_type="product_cost",
            cost_name="商品成本",
            amount=product_cost
        ))
    if meal_cost > 0:
        cost_details.append(CostDetailItem(
            cost_type="meal_cost",
            cost_name="餐费成本",
            amount=meal_cost
        ))
    
    # 查询当天的客户借款和还款记录
    customer_financials_dict = {}
    
    # 查询当天的借款记录
    loans = db.query(CustomerLoan).filter(
        and_(
            CustomerLoan.created_at >= start_datetime,
            CustomerLoan.created_at <= end_datetime
        )
    ).all()
    
    for loan in loans:
        customer_id = loan.customer_id
        if customer_id not in customer_financials_dict:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            customer_financials_dict[customer_id] = {
                "customer_id": customer_id,
                "customer_name": customer.name if customer else f"客户{customer_id}",
                "loan_amount": Decimal("0"),
                "repayment_amount": Decimal("0"),
                "current_balance": customer.balance if customer else Decimal("0")
            }
        customer_financials_dict[customer_id]["loan_amount"] += loan.amount or Decimal("0")
    
    # 查询当天的还款记录
    repayments = db.query(CustomerRepayment).filter(
        and_(
            CustomerRepayment.created_at >= start_datetime,
            CustomerRepayment.created_at <= end_datetime
        )
    ).all()
    
    for repayment in repayments:
        customer_id = repayment.customer_id
        if customer_id not in customer_financials_dict:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            customer_financials_dict[customer_id] = {
                "customer_id": customer_id,
                "customer_name": customer.name if customer else f"客户{customer_id}",
                "loan_amount": Decimal("0"),
                "repayment_amount": Decimal("0"),
                "current_balance": customer.balance if customer else Decimal("0")
            }
        customer_financials_dict[customer_id]["repayment_amount"] += repayment.amount or Decimal("0")
    
    # 构建客户财务详情列表
    customer_financials = [
        CustomerFinancialItem(
            customer_id=details["customer_id"],
            customer_name=details["customer_name"],
            loan_amount=details["loan_amount"],
            repayment_amount=details["repayment_amount"],
            current_balance=details["current_balance"]
        )
        for details in customer_financials_dict.values()
    ]
    
    return DailyStatisticsResponse(
        date=target_date,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_profit=total_profit,
        other_income=other_income_total,
        other_expense=other_expense_total,
        table_fee_total=table_fee_total,
        product_revenue=product_revenue,
        product_cost=product_cost,
        meal_revenue=meal_revenue,
        meal_cost=meal_cost,
        session_count=len(sessions),
        room_count=len(room_ids),
        room_details=room_details,
        cost_details=cost_details,
        customer_financials=customer_financials
    )


@router.get("/monthly", response_model=MonthlyStatisticsResponse)
def get_monthly_statistics(
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份（1-12）"),
    db: Session = Depends(get_db)
):
    """获取每月统计"""
    # 计算月份的开始和结束日期
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # 查询当月的房间使用记录
    sessions = db.query(RoomSession).filter(
        and_(
            RoomSession.start_time >= start_datetime,
            RoomSession.start_time <= end_datetime,
            RoomSession.status == "settled"
        )
    ).all()
    
    # 计算统计数据
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    table_fee_total = Decimal("0")
    product_revenue = Decimal("0")
    product_cost = Decimal("0")
    meal_revenue = Decimal("0")
    meal_cost = Decimal("0")
    room_ids = set()
    
    # 按日期分组统计
    daily_stats_dict = {}
    
    for session in sessions:
        session_date = session.start_time.date()
        if session_date not in daily_stats_dict:
            daily_stats_dict[session_date] = {
                "revenue": Decimal("0"),
                "cost": Decimal("0"),
                "table_fee": Decimal("0"),
                "product_revenue": Decimal("0"),
                "product_cost": Decimal("0"),
                "meal_revenue": Decimal("0"),
                "meal_cost": Decimal("0"),
                "session_count": 0,
                "room_ids": set()
            }
        
        daily_stats_dict[session_date]["revenue"] += session.total_revenue or Decimal("0")
        daily_stats_dict[session_date]["cost"] += session.total_cost or Decimal("0")
        daily_stats_dict[session_date]["table_fee"] += session.table_fee or Decimal("0")
        daily_stats_dict[session_date]["session_count"] += 1
        daily_stats_dict[session_date]["room_ids"].add(session.room_id)
        
        total_revenue += session.total_revenue or Decimal("0")
        total_cost += session.total_cost or Decimal("0")
        table_fee_total += session.table_fee or Decimal("0")
        room_ids.add(session.room_id)
        
        # 查询商品消费
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session.id
        ).all()
        for consumption in consumptions:
            daily_stats_dict[session_date]["product_revenue"] += consumption.total_price or Decimal("0")
            daily_stats_dict[session_date]["product_cost"] += consumption.total_cost or Decimal("0")
            product_revenue += consumption.total_price or Decimal("0")
            product_cost += consumption.total_cost or Decimal("0")
        
        # 查询餐费
        meals = db.query(MealRecord).filter(
            MealRecord.session_id == session.id
        ).all()
        for meal in meals:
            daily_stats_dict[session_date]["meal_revenue"] += meal.amount or Decimal("0")
            daily_stats_dict[session_date]["meal_cost"] += meal.cost_price or Decimal("0")
            meal_revenue += meal.amount or Decimal("0")
            meal_cost += meal.cost_price or Decimal("0")
    
    # 查询当月的其它支出和收入
    other_expenses = db.query(OtherExpense).filter(
        and_(
            OtherExpense.expense_date >= start_datetime,
            OtherExpense.expense_date <= end_datetime
        )
    ).all()
    
    other_incomes = db.query(OtherIncome).filter(
        and_(
            OtherIncome.income_date >= start_datetime,
            OtherIncome.income_date <= end_datetime
        )
    ).all()
    
    other_expense_total = sum(exp.amount for exp in other_expenses)
    other_income_total = sum(inc.amount for inc in other_incomes)
    
    # 按日期分组统计其它支出和收入
    daily_other_expense_dict = {}
    daily_other_income_dict = {}
    
    for exp in other_expenses:
        exp_date = exp.expense_date.date()
        if exp_date not in daily_other_expense_dict:
            daily_other_expense_dict[exp_date] = Decimal("0")
        daily_other_expense_dict[exp_date] += exp.amount
    
    for inc in other_incomes:
        inc_date = inc.income_date.date()
        if inc_date not in daily_other_income_dict:
            daily_other_income_dict[inc_date] = Decimal("0")
        daily_other_income_dict[inc_date] += inc.amount
    
    # 利润 = 房间收入 - 房间成本 + 其它收入 - 其它支出
    total_profit = table_fee_total - product_cost - meal_cost + other_income_total - other_expense_total
    
    # 构建每日统计列表
    daily_statistics = []
    for stat_date, stats in sorted(daily_stats_dict.items()):
        daily_other_income = daily_other_income_dict.get(stat_date, Decimal("0"))
        daily_other_expense = daily_other_expense_dict.get(stat_date, Decimal("0"))
        daily_profit = stats["table_fee"] - stats["product_cost"] - stats["meal_cost"] + daily_other_income - daily_other_expense
        daily_statistics.append(DailyStatisticsResponse(
            date=stat_date,
            total_revenue=stats["revenue"],
            total_cost=stats["cost"],
            total_profit=daily_profit,
            other_income=daily_other_income,
            other_expense=daily_other_expense,
            table_fee_total=stats["table_fee"],
            product_revenue=stats["product_revenue"],
            product_cost=stats["product_cost"],
            meal_revenue=stats["meal_revenue"],
            meal_cost=stats["meal_cost"],
            session_count=stats["session_count"],
            room_count=len(stats["room_ids"])
        ))
    
    return MonthlyStatisticsResponse(
        year=year,
        month=month,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_profit=total_profit,
        other_income=other_income_total,
        other_expense=other_expense_total,
        table_fee_total=table_fee_total,
        product_revenue=product_revenue,
        product_cost=product_cost,
        meal_revenue=meal_revenue,
        meal_cost=meal_cost,
        session_count=len(sessions),
        room_count=len(room_ids),
        daily_statistics=daily_statistics
    )


@router.get("/customer-ranking", response_model=List[CustomerRankingItem])
def get_customer_ranking(
    rank_type: str = Query("consumption", description="排行类型：consumption=消费排行, balance=欠款排行"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取客户消费排行"""
    # 获取所有客户
    customers = db.query(Customer).all()
    
    ranking_items = []
    
    for customer in customers:
        # 计算商品消费
        product_consumption = db.query(
            func.sum(ProductConsumption.total_price)
        ).filter(
            ProductConsumption.customer_id == customer.id
        ).scalar() or Decimal("0")
        
        # 计算餐费消费
        meal_consumption = db.query(
            func.sum(MealRecord.amount)
        ).filter(
            MealRecord.customer_id == customer.id
        ).scalar() or Decimal("0")
        
        total_consumption = product_consumption + meal_consumption
        
        # 计算总借款
        total_loans = db.query(
            func.sum(CustomerLoan.amount)
        ).filter(
            CustomerLoan.customer_id == customer.id
        ).scalar() or Decimal("0")
        
        # 计算参与房间使用次数
        session_count = db.query(
            func.count(func.distinct(ProductConsumption.session_id))
        ).filter(
            ProductConsumption.customer_id == customer.id
        ).scalar() or 0
        
        meal_session_count = db.query(
            func.count(func.distinct(MealRecord.session_id))
        ).filter(
            MealRecord.customer_id == customer.id
        ).scalar() or 0
        
        session_count = max(session_count, meal_session_count)
        
        ranking_items.append(CustomerRankingItem(
            customer_id=customer.id,
            customer_name=customer.name,
            total_consumption=total_consumption,
            total_loans=total_loans,
            current_balance=customer.balance or Decimal("0"),
            session_count=session_count
        ))
    
    # 排序
    if rank_type == "consumption":
        ranking_items.sort(key=lambda x: x.total_consumption, reverse=True)
    else:
        ranking_items.sort(key=lambda x: x.current_balance, reverse=True)
    
    return ranking_items[:limit]


@router.get("/room-usage", response_model=List[RoomUsageItem])
def get_room_usage(
    db: Session = Depends(get_db)
):
    """获取房间使用率统计"""
    # 获取所有房间
    rooms = db.query(Room).all()
    
    usage_items = []
    
    for room in rooms:
        # 查询该房间的所有已结算记录
        sessions = db.query(RoomSession).filter(
            RoomSession.room_id == room.id,
            RoomSession.status == "settled"
        ).all()
        
        session_count = len(sessions)
        total_hours = Decimal("0")
        total_revenue = Decimal("0")
        total_profit = Decimal("0")
        
        for session in sessions:
            if session.end_time and session.start_time:
                # 计算使用时长（小时）
                duration = session.end_time - session.start_time
                hours = Decimal(str(duration.total_seconds() / 3600))
                total_hours += hours
            
            total_revenue += session.total_revenue or Decimal("0")
            total_profit += session.total_profit or Decimal("0")
        
        if session_count > 0:
            usage_items.append(RoomUsageItem(
                room_id=room.id,
                room_name=room.name,
                session_count=session_count,
                total_hours=total_hours,
                total_revenue=total_revenue,
                total_profit=total_profit
            ))
    
    # 按使用次数排序
    usage_items.sort(key=lambda x: x.session_count, reverse=True)
    
    return usage_items


@router.get("/product-sales", response_model=List[ProductSalesItem])
def get_product_sales(
    db: Session = Depends(get_db)
):
    """获取商品销售统计"""
    query = db.query(
        Product.id,
        Product.name,
        func.sum(ProductConsumption.quantity).label("total_quantity"),
        func.sum(ProductConsumption.total_price).label("total_revenue"),
        func.sum(ProductConsumption.total_cost).label("total_cost")
    ).join(
        ProductConsumption, ProductConsumption.product_id == Product.id
    ).filter(
        Product.product_type == "normal"
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(ProductConsumption.total_price).desc()
    )
    
    results = query.all()
    
    sales_items = []
    for result in results:
        total_profit = (result.total_revenue or Decimal("0")) - (result.total_cost or Decimal("0"))
        sales_items.append(ProductSalesItem(
            product_id=result.id,
            product_name=result.name,
            total_quantity=result.total_quantity or 0,
            total_revenue=result.total_revenue or Decimal("0"),
            total_cost=result.total_cost or Decimal("0"),
            total_profit=total_profit
        ))
    
    return sales_items

