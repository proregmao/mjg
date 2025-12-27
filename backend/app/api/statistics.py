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
from app.models.session_result import SessionResult
from app.schemas.statistics import (
    DailyStatisticsResponse, MonthlyStatisticsResponse,
    CustomerRankingItem, RoomUsageItem, ProductSalesItem,
    RoomDetailItem, CostDetailItem, CustomerFinancialItem,
    TableFeeDetailItem, OtherIncomeDetailItem, OtherExpenseDetailItem,
    WinLossRankingResponse, WinLossItem, WinLossSummary
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
        # 注意：total_revenue 只计算台子费总额，因为台子费已包含商品消费和餐费
        # 不重复计算商品收入和餐费收入
        total_cost += session.total_cost or Decimal("0")
        table_fee = session.table_fee or Decimal("0")
        table_fee_total += table_fee
        # 今日收入 = 台子费总额（台子费已包含商品消费和餐费）
        total_revenue += table_fee
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
    
    # 台子费利润 = 台子费 - 商品成本 - 餐费成本
    table_fee_profit = table_fee_total - product_cost - meal_cost
    
    # 总利润 = 台子费利润 + 其它收入 - 其它支出
    total_profit = table_fee_profit + other_income_total - other_expense_total
    
    # 构建台子费明细清单
    table_fee_details = []
    for session in sessions:
        # 计算该会话的商品成本和餐费成本
        session_product_cost = Decimal("0")
        session_meal_cost = Decimal("0")
        
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session.id
        ).all()
        for consumption in consumptions:
            session_product_cost += consumption.total_cost or Decimal("0")
        
        meals = db.query(MealRecord).filter(
            MealRecord.session_id == session.id
        ).all()
        for meal in meals:
            session_meal_cost += meal.cost_price or Decimal("0")
        
        table_fee = session.table_fee or Decimal("0")
        session_profit = table_fee - session_product_cost - session_meal_cost
        
        room = db.query(Room).filter(Room.id == session.room_id).first()
        table_fee_details.append(TableFeeDetailItem(
            session_id=session.id,
            room_id=session.room_id,
            room_name=room.name if room else f"房间{session.room_id}",
            table_fee=table_fee,
            product_cost=session_product_cost,
            meal_cost=session_meal_cost,
            profit=session_profit,
            start_time=session.start_time
        ))
    
    # 构建其它收入明细清单
    other_income_details = [
        OtherIncomeDetailItem(
            id=income.id,
            name=income.name,
            amount=income.amount,
            payment_method=income.payment_method or "现金",
            income_date=income.income_date,
            description=income.description
        )
        for income in other_incomes
    ]
    
    # 构建其它支出明细清单
    other_expense_details = [
        OtherExpenseDetailItem(
            id=expense.id,
            name=expense.name,
            amount=expense.amount,
            payment_method=expense.payment_method or "现金",
            expense_date=expense.expense_date,
            description=expense.description
        )
        for expense in other_expenses
    ]
    
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
        table_fee_profit=table_fee_profit,
        product_revenue=product_revenue,
        product_cost=product_cost,
        meal_revenue=meal_revenue,
        meal_cost=meal_cost,
        session_count=len(sessions),
        room_count=len(room_ids),
        room_details=room_details,
        cost_details=cost_details,
        customer_financials=customer_financials,
        table_fee_details=table_fee_details,
        other_income_details=other_income_details,
        other_expense_details=other_expense_details
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
        
        # 注意：revenue 只计算台子费，因为台子费已包含商品消费和餐费
        table_fee = session.table_fee or Decimal("0")
        daily_stats_dict[session_date]["revenue"] += table_fee
        daily_stats_dict[session_date]["cost"] += session.total_cost or Decimal("0")
        daily_stats_dict[session_date]["table_fee"] += table_fee
        daily_stats_dict[session_date]["session_count"] += 1
        daily_stats_dict[session_date]["room_ids"].add(session.room_id)
        
        # 今日收入 = 台子费总额（台子费已包含商品消费和餐费）
        total_revenue += table_fee
        total_cost += session.total_cost or Decimal("0")
        table_fee_total += table_fee
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
    
    # 台子费利润 = 台子费 - 商品成本 - 餐费成本
    table_fee_profit = table_fee_total - product_cost - meal_cost
    
    # 总利润 = 台子费利润 + 其它收入 - 其它支出
    total_profit = table_fee_profit + other_income_total - other_expense_total
    
    # 构建每日统计列表
    daily_statistics = []
    for stat_date, stats in sorted(daily_stats_dict.items()):
        daily_other_income = daily_other_income_dict.get(stat_date, Decimal("0"))
        daily_other_expense = daily_other_expense_dict.get(stat_date, Decimal("0"))
        daily_table_fee_profit = stats["table_fee"] - stats["product_cost"] - stats["meal_cost"]
        daily_profit = daily_table_fee_profit + daily_other_income - daily_other_expense
        
        # 获取当天的会话列表
        daily_sessions = [s for s in sessions if s.start_time.date() == stat_date]
        
        # 构建当天的台子费明细
        daily_table_fee_details = []
        for session in daily_sessions:
            session_product_cost = Decimal("0")
            session_meal_cost = Decimal("0")
            
            consumptions = db.query(ProductConsumption).filter(
                ProductConsumption.session_id == session.id
            ).all()
            for consumption in consumptions:
                session_product_cost += consumption.total_cost or Decimal("0")
            
            meals = db.query(MealRecord).filter(
                MealRecord.session_id == session.id
            ).all()
            for meal in meals:
                session_meal_cost += meal.cost_price or Decimal("0")
            
            table_fee = session.table_fee or Decimal("0")
            session_profit = table_fee - session_product_cost - session_meal_cost
            
            room = db.query(Room).filter(Room.id == session.room_id).first()
            daily_table_fee_details.append(TableFeeDetailItem(
                session_id=session.id,
                room_id=session.room_id,
                room_name=room.name if room else f"房间{session.room_id}",
                table_fee=table_fee,
                product_cost=session_product_cost,
                meal_cost=session_meal_cost,
                profit=session_profit,
                start_time=session.start_time
            ))
        
        # 构建当天的其它收入和支出明细
        daily_other_income_details = [
            OtherIncomeDetailItem(
                id=income.id,
                name=income.name,
                amount=income.amount,
                payment_method=income.payment_method or "现金",
                income_date=income.income_date,
                description=income.description
            )
            for income in other_incomes if income.income_date.date() == stat_date
        ]
        
        daily_other_expense_details = [
            OtherExpenseDetailItem(
                id=expense.id,
                name=expense.name,
                amount=expense.amount,
                payment_method=expense.payment_method or "现金",
                expense_date=expense.expense_date,
                description=expense.description
            )
            for expense in other_expenses if expense.expense_date.date() == stat_date
        ]
        
        # 注意：total_revenue 只计算台子费总额，因为台子费已包含商品消费和餐费
        daily_statistics.append(DailyStatisticsResponse(
            date=stat_date,
            total_revenue=stats["table_fee"],  # 使用台子费作为收入，因为台子费已包含商品消费和餐费
            total_cost=stats["cost"],
            total_profit=daily_profit,
            other_income=daily_other_income,
            other_expense=daily_other_expense,
            table_fee_total=stats["table_fee"],
            table_fee_profit=daily_table_fee_profit,
            product_revenue=stats["product_revenue"],
            product_cost=stats["product_cost"],
            meal_revenue=stats["meal_revenue"],
            meal_cost=stats["meal_cost"],
            session_count=stats["session_count"],
            room_count=len(stats["room_ids"]),
            table_fee_details=daily_table_fee_details,
            other_income_details=daily_other_income_details,
            other_expense_details=daily_other_expense_details
        ))
    
    # 构建全月台子费明细清单
    table_fee_details = []
    for session in sessions:
        # 计算该会话的商品成本和餐费成本
        session_product_cost = Decimal("0")
        session_meal_cost = Decimal("0")
        
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session.id
        ).all()
        for consumption in consumptions:
            session_product_cost += consumption.total_cost or Decimal("0")
        
        meals = db.query(MealRecord).filter(
            MealRecord.session_id == session.id
        ).all()
        for meal in meals:
            session_meal_cost += meal.cost_price or Decimal("0")
        
        table_fee = session.table_fee or Decimal("0")
        session_profit = table_fee - session_product_cost - session_meal_cost
        
        room = db.query(Room).filter(Room.id == session.room_id).first()
        table_fee_details.append(TableFeeDetailItem(
            session_id=session.id,
            room_id=session.room_id,
            room_name=room.name if room else f"房间{session.room_id}",
            table_fee=table_fee,
            product_cost=session_product_cost,
            meal_cost=session_meal_cost,
            profit=session_profit,
            start_time=session.start_time
        ))
    
    # 构建全月其它收入明细清单
    other_income_details = [
        OtherIncomeDetailItem(
            id=income.id,
            name=income.name,
            amount=income.amount,
            payment_method=income.payment_method or "现金",
            income_date=income.income_date,
            description=income.description
        )
        for income in other_incomes
    ]
    
    # 构建全月其它支出明细清单
    other_expense_details = [
        OtherExpenseDetailItem(
            id=expense.id,
            name=expense.name,
            amount=expense.amount,
            payment_method=expense.payment_method or "现金",
            expense_date=expense.expense_date,
            description=expense.description
        )
        for expense in other_expenses
    ]
    
    return MonthlyStatisticsResponse(
        year=year,
        month=month,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_profit=total_profit,
        other_income=other_income_total,
        other_expense=other_expense_total,
        table_fee_total=table_fee_total,
        table_fee_profit=table_fee_profit,
        product_revenue=product_revenue,
        product_cost=product_cost,
        meal_revenue=meal_revenue,
        meal_cost=meal_cost,
        session_count=len(sessions),
        room_count=len(room_ids),
        daily_statistics=daily_statistics,
        table_fee_details=table_fee_details,
        other_income_details=other_income_details,
        other_expense_details=other_expense_details
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
            
            # 注意：total_revenue 只计算台子费，因为台子费已包含商品消费和餐费
            table_fee = session.table_fee or Decimal("0")
            total_revenue += table_fee
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


@router.get("/win-loss-ranking", response_model=WinLossRankingResponse)
def get_win_loss_ranking(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取客户输赢榜"""
    # 转换日期为datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # 1. 获取时间段内所有的已结算的session
    sessions = db.query(RoomSession).filter(
        and_(
            RoomSession.start_time >= start_datetime,
            RoomSession.start_time <= end_datetime,
            RoomSession.status == "settled"
        )
    ).all()
    
    session_ids = [s.id for s in sessions]
    
    # 2. 计算时间段内总台费
    total_table_fee = sum(s.table_fee or Decimal("0") for s in sessions)

    # 3. 获取所有客户
    customers = db.query(Customer).all()
    
    # 预取所有相关数据以在内存中处理（避免N+1查询）
    # 1. 输赢结果
    session_results = db.query(SessionResult).filter(
        SessionResult.session_id.in_(session_ids)
    ).all()
    
    # 2. 借款记录
    loans = db.query(CustomerLoan).filter(
         CustomerLoan.session_id.in_(session_ids)
    ).all()
    
    # 3. 还款记录
    repayments = db.query(CustomerRepayment).filter(
         CustomerRepayment.session_id.in_(session_ids)
    ).all()
    
    # 组织数据： {(session_id, customer_id): {loan: 0, repay: 0, manual: None}}
    session_customer_map = {}
    
    def get_sc_item(s_id, c_id):
        key = (s_id, c_id)
        if key not in session_customer_map:
            session_customer_map[key] = {'loan': Decimal(0), 'repay': Decimal(0), 'manual': None}
        return session_customer_map[key]

    for l in loans:
        item = get_sc_item(l.session_id, l.customer_id)
        item['loan'] += (l.amount or Decimal(0))
        
    for r in repayments:
         item = get_sc_item(r.session_id, r.customer_id)
         item['repay'] += (r.amount or Decimal(0))
         
    for res in session_results:
        item = get_sc_item(res.session_id, res.customer_id)
        item['manual'] = res.net_win_loss

    ranking_items = []
    
    for customer in customers:
        total_loan = Decimal(0)
        total_repayment = Decimal(0)
        net_win_loss = Decimal(0)
        involved_sessions = set()
        
        # 遍历该客户参与的所有session数据
        # 这种遍历方式效率稍低，但鉴于customer数量和session数量，通常可接受。
        # 更优做法是遍历 session_customer_map 聚合到 customer_map，再生成 list
        
        # 优化：先聚合
        # customer_agg = { cust_id: { loan, repay, win_loss, sessions } }
        pass

    # 由于上面循环重构了，这里直接基于 session_customer_map 聚合
    customer_agg = {}
    
    for (s_id, c_id), data in session_customer_map.items():
        if c_id not in customer_agg:
            customer_agg[c_id] = {
                'loan': Decimal(0), 
                'repay': Decimal(0), 
                'win_loss': Decimal(0), 
                'sessions': set()
            }
        
        # 借还款总额始终累加（用于展示）
        customer_agg[c_id]['loan'] += data['loan']
        customer_agg[c_id]['repay'] += data['repay']
        customer_agg[c_id]['sessions'].add(s_id)
        
        # 输赢计算：如果有手动结果，用手动的；否则用 (还 - 借)
        if data['manual'] is not None:
            customer_agg[c_id]['win_loss'] += data['manual']
        else:
            customer_agg[c_id]['win_loss'] += (data['repay'] - data['loan'])

    # 构建 ranking_items
    for customer in customers:
        if customer.id in customer_agg:
            agg = customer_agg[customer.id]
            ranking_items.append(WinLossItem(
                customer_id=customer.id,
                customer_name=customer.name,
                customer_phone=customer.phone,
                total_loan=agg['loan'],
                total_repayment=agg['repay'],
                net_win_loss=agg['win_loss'],
                session_count=len(agg['sessions'])
            ))

    # 4. 排序：按净输赢降序（赢钱多的在前）
    ranking_items.sort(key=lambda x: x.net_win_loss, reverse=True)
    
    # 5. 计算汇总
    total_win = sum(item.net_win_loss for item in ranking_items if item.net_win_loss > 0)
    total_loss = sum(item.net_win_loss for item in ranking_items if item.net_win_loss < 0)
    
    return WinLossRankingResponse(
        start_date=start_date,
        end_date=end_date,
        ranking=ranking_items,
        summary=WinLossSummary(
            total_win=total_win,
            total_loss=total_loss, # 这是一个负数
            total_table_fee=total_table_fee
        )
    )


