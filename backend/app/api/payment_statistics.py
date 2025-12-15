"""
支付方式统计API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List
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
from app.models.customer import Customer
from app.models.room import Room
from app.models.cash_transfer import CashTransfer
from pydantic import BaseModel, Field, ConfigDict

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
    
    # 统计房间收入（只统计台子费，因为台子费已包含商品消费和餐费）
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
        
        # 台子费（台子费已包含商品消费和餐费，所以只统计台子费）
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
        
        # 注意：商品消费和餐费不单独统计，因为它们已包含在台子费中
    
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
    
    # 统计从银行取现（增加现金，但不产生利润，所以不统计在breakdown中）
    if date_filter:
        transfers_query = db.query(CashTransfer).filter(CashTransfer.transfer_type == "bank_to_cash")
        if start_datetime:
            transfers_query = transfers_query.filter(CashTransfer.transfer_date >= start_datetime)
        if end_datetime:
            transfers_query = transfers_query.filter(CashTransfer.transfer_date <= end_datetime)
        transfers = transfers_query.all()
    else:
        transfers = db.query(CashTransfer).filter(CashTransfer.transfer_type == "bank_to_cash").all()
    
    for transfer in transfers:
        if date_filter and not date_filter(transfer.transfer_date):
            continue
        # 从银行取现增加现金余额，但不产生利润，所以不统计在breakdown中
        cash_total += transfer.amount
    
    # 统计存入银行/取现（减少现金，但不产生利润，所以不统计在breakdown中）
    if date_filter:
        cash_to_bank_query = db.query(CashTransfer).filter(CashTransfer.transfer_type == "cash_to_bank")
        if start_datetime:
            cash_to_bank_query = cash_to_bank_query.filter(CashTransfer.transfer_date >= start_datetime)
        if end_datetime:
            cash_to_bank_query = cash_to_bank_query.filter(CashTransfer.transfer_date <= end_datetime)
        cash_to_bank_transfers = cash_to_bank_query.all()
    else:
        cash_to_bank_transfers = db.query(CashTransfer).filter(CashTransfer.transfer_type == "cash_to_bank").all()
    
    for transfer in cash_to_bank_transfers:
        if date_filter and not date_filter(transfer.transfer_date):
            continue
        # 存入银行/取现减少现金余额，但不产生利润，所以不统计在breakdown中
        cash_total -= transfer.amount
    
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


class CashFlowItem(BaseModel):
    """现金流水项"""
    model_config = ConfigDict(populate_by_name=True)
    
    id: int = Field(..., description="记录ID")
    type: str = Field(..., description="类型：loan=借款, repayment=还款, room_income=房间收入, other_income=其它收入, other_expense=其它支出, bank_to_cash=从银行取现, cash_to_bank=存入银行/取现")
    amount: Decimal = Field(..., description="金额（正数表示增加，负数表示减少）")
    record_datetime: datetime = Field(..., description="时间", alias="datetime")
    description: str = Field(..., description="描述")
    customer_name: Optional[str] = Field(None, description="客户名称")
    room_name: Optional[str] = Field(None, description="房间名称")
    payment_method: str = Field(..., description="支付方式")
    cash_balance: Decimal = Field(..., description="现金余额（该笔交易后的余额）")
    transfer_id: Optional[int] = Field(None, description="转账记录ID（仅bank_to_cash类型有）")


class CashFlowListResponse(BaseModel):
    """现金流水列表响应模型"""
    items: List[CashFlowItem] = Field(default_factory=list, description="流水列表")
    total: int = Field(..., description="总记录数")


@router.get("/cash-flow", response_model=CashFlowListResponse)
def get_cash_flow(
    start_date: Optional[date] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """
    获取现金流水明细列表
    支持按日期范围过滤，返回所有现金相关的记录
    """
    # 获取初期现金
    initial_cash_config = db.query(SystemConfig).filter(SystemConfig.key == "initial_cash").first()
    initial_cash = Decimal(initial_cash_config.value) if initial_cash_config else Decimal("0")
    
    items = []
    
    # 构建日期过滤条件
    start_datetime = None
    end_datetime = None
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # 计算起始余额（日期范围之前的所有现金交易）
    starting_balance = initial_cash
    if start_datetime:
        # 计算start_datetime之前的所有现金交易
        # 借款（减少）
        loans_before = db.query(CustomerLoan).filter(
            CustomerLoan.created_at < start_datetime,
            (CustomerLoan.payment_method == "现金") | (CustomerLoan.payment_method.is_(None))
        ).all()
        for loan in loans_before:
            starting_balance -= loan.amount
        
        # 还款（增加）
        repayments_before = db.query(CustomerRepayment).filter(
            CustomerRepayment.created_at < start_datetime,
            (CustomerRepayment.payment_method == "现金") | (CustomerRepayment.payment_method.is_(None))
        ).all()
        for repayment in repayments_before:
            starting_balance += repayment.amount
        
        # 房间收入（增加）
        sessions_before = db.query(RoomSession).filter(
            RoomSession.status == "settled",
            RoomSession.start_time < start_datetime,
            (RoomSession.table_fee_payment_method == "现金") | (RoomSession.table_fee_payment_method.is_(None))
        ).all()
        for session in sessions_before:
            if session.table_fee and session.table_fee > 0:
                starting_balance += session.table_fee
        
        # 其它收入（增加）
        incomes_before = db.query(OtherIncome).filter(
            OtherIncome.income_date < start_datetime,
            (OtherIncome.payment_method == "现金") | (OtherIncome.payment_method.is_(None))
        ).all()
        for income in incomes_before:
            starting_balance += income.amount
        
        # 其它支出（减少）
        expenses_before = db.query(OtherExpense).filter(
            OtherExpense.expense_date < start_datetime,
            (OtherExpense.payment_method == "现金") | (OtherExpense.payment_method.is_(None))
        ).all()
        for expense in expenses_before:
            starting_balance -= expense.amount
        
        # 从银行取现（增加）
        transfers_before = db.query(CashTransfer).filter(
            CashTransfer.transfer_date < start_datetime,
            CashTransfer.transfer_type == "bank_to_cash"
        ).all()
        for transfer in transfers_before:
            starting_balance += transfer.amount
        
        # 存入银行/取现（减少）
        cash_to_bank_before = db.query(CashTransfer).filter(
            CashTransfer.transfer_date < start_datetime,
            CashTransfer.transfer_type == "cash_to_bank"
        ).all()
        for transfer in cash_to_bank_before:
            starting_balance -= transfer.amount
    
    # 1. 获取借款记录（现金支付）
    loans_query = db.query(CustomerLoan).join(Customer, CustomerLoan.customer_id == Customer.id)
    if start_datetime:
        loans_query = loans_query.filter(CustomerLoan.created_at >= start_datetime)
    if end_datetime:
        loans_query = loans_query.filter(CustomerLoan.created_at <= end_datetime)
    loans = loans_query.filter(
        (CustomerLoan.payment_method == "现金") | (CustomerLoan.payment_method.is_(None))
    ).all()
    
    for loan in loans:
        items.append(CashFlowItem(
            id=loan.id,
            type="loan",
            amount=-loan.amount,  # 借款为负数
            record_datetime=loan.created_at,
            description=f"借款 - {loan.customer.name if loan.customer else '未知客户'}",
            customer_name=loan.customer.name if loan.customer else None,
            room_name=None,
            payment_method=loan.payment_method or "现金",
            cash_balance=Decimal("0")  # 稍后计算
        ))
    
    # 2. 获取还款记录（现金支付）
    repayments_query = db.query(CustomerRepayment).join(Customer, CustomerRepayment.customer_id == Customer.id)
    if start_datetime:
        repayments_query = repayments_query.filter(CustomerRepayment.created_at >= start_datetime)
    if end_datetime:
        repayments_query = repayments_query.filter(CustomerRepayment.created_at <= end_datetime)
    repayments = repayments_query.filter(
        (CustomerRepayment.payment_method == "现金") | (CustomerRepayment.payment_method.is_(None))
    ).all()
    
    for repayment in repayments:
        items.append(CashFlowItem(
            id=repayment.id,
            type="repayment",
            amount=repayment.amount,  # 还款为正数
            record_datetime=repayment.created_at,
            description=f"还款 - {repayment.customer.name if repayment.customer else '未知客户'}",
            customer_name=repayment.customer.name if repayment.customer else None,
            room_name=None,
            payment_method=repayment.payment_method or "现金",
            cash_balance=Decimal("0")  # 稍后计算
        ))
    
    # 3. 获取房间收入（台子费，现金支付）
    sessions_query = db.query(RoomSession).join(Room, RoomSession.room_id == Room.id)
    sessions_query = sessions_query.filter(RoomSession.status == "settled")
    if start_datetime:
        sessions_query = sessions_query.filter(RoomSession.start_time >= start_datetime)
    if end_datetime:
        sessions_query = sessions_query.filter(RoomSession.start_time <= end_datetime)
    sessions = sessions_query.filter(
        (RoomSession.table_fee_payment_method == "现金") | (RoomSession.table_fee_payment_method.is_(None))
    ).all()
    
    for session in sessions:
        if session.table_fee and session.table_fee > 0:
            items.append(CashFlowItem(
                id=session.id,
                type="room_income",
                amount=session.table_fee,  # 房间收入为正数
                record_datetime=session.start_time,
                description=f"房间收入（台子费） - {session.room.name if session.room else '未知房间'}",
                customer_name=None,
                room_name=session.room.name if session.room else None,
                payment_method=session.table_fee_payment_method or "现金",
                cash_balance=Decimal("0")  # 稍后计算
            ))
    
    # 4. 获取其它收入（现金支付）
    other_incomes_query = db.query(OtherIncome)
    if start_datetime:
        other_incomes_query = other_incomes_query.filter(OtherIncome.income_date >= start_datetime)
    if end_datetime:
        other_incomes_query = other_incomes_query.filter(OtherIncome.income_date <= end_datetime)
    other_incomes = other_incomes_query.filter(
        (OtherIncome.payment_method == "现金") | (OtherIncome.payment_method.is_(None))
    ).all()
    
    for income in other_incomes:
        items.append(CashFlowItem(
            id=income.id,
            type="other_income",
            amount=income.amount,  # 其它收入为正数
            record_datetime=income.income_date,
            description=f"其它收入 - {income.name}",
            customer_name=None,
            room_name=None,
            payment_method=income.payment_method or "现金",
            cash_balance=Decimal("0")  # 稍后计算
        ))
    
    # 5. 获取其它支出（现金支付）
    other_expenses_query = db.query(OtherExpense)
    if start_datetime:
        other_expenses_query = other_expenses_query.filter(OtherExpense.expense_date >= start_datetime)
    if end_datetime:
        other_expenses_query = other_expenses_query.filter(OtherExpense.expense_date <= end_datetime)
    other_expenses = other_expenses_query.filter(
        (OtherExpense.payment_method == "现金") | (OtherExpense.payment_method.is_(None))
    ).all()
    
    for expense in other_expenses:
        items.append(CashFlowItem(
            id=expense.id,
            type="other_expense",
            amount=-expense.amount,  # 其它支出为负数
            record_datetime=expense.expense_date,
            description=f"其它支出 - {expense.name}",
            customer_name=None,
            room_name=None,
            payment_method=expense.payment_method or "现金",
            cash_balance=Decimal("0")  # 稍后计算
        ))
    
    # 6. 获取从银行取现记录
    transfers_query = db.query(CashTransfer).filter(
        CashTransfer.transfer_type == "bank_to_cash"
    )
    if start_datetime:
        transfers_query = transfers_query.filter(CashTransfer.transfer_date >= start_datetime)
    if end_datetime:
        transfers_query = transfers_query.filter(CashTransfer.transfer_date <= end_datetime)
    transfers = transfers_query.all()
    
    for transfer in transfers:
        items.append(CashFlowItem(
            id=transfer.id,
            type="bank_to_cash",
            amount=transfer.amount,  # 从银行取现为正数（增加现金）
            record_datetime=transfer.transfer_date,
            description=transfer.description or "",  # 直接返回原始描述，不拼接前缀
            customer_name=None,
            room_name=None,
            payment_method="银行转账",
            cash_balance=Decimal("0"),  # 稍后计算
            transfer_id=transfer.id  # 添加transfer_id用于更新
        ))
    
    # 7. 获取存入银行/取现记录
    cash_to_bank_query = db.query(CashTransfer).filter(
        CashTransfer.transfer_type == "cash_to_bank"
    )
    if start_datetime:
        cash_to_bank_query = cash_to_bank_query.filter(CashTransfer.transfer_date >= start_datetime)
    if end_datetime:
        cash_to_bank_query = cash_to_bank_query.filter(CashTransfer.transfer_date <= end_datetime)
    cash_to_bank_transfers = cash_to_bank_query.all()
    
    for transfer in cash_to_bank_transfers:
        items.append(CashFlowItem(
            id=transfer.id,
            type="cash_to_bank",
            amount=-transfer.amount,  # 存入银行/取现为负数（减少现金）
            record_datetime=transfer.transfer_date,
            description=transfer.description or "",  # 直接返回原始描述，不拼接前缀
            customer_name=None,
            room_name=None,
            payment_method="银行转账",
            cash_balance=Decimal("0"),  # 稍后计算
            transfer_id=transfer.id  # 添加transfer_id用于更新
        ))
    
    # 按时间正序排序（从早到晚），如果时间相同则按ID正序，用于计算余额
    # 这样确保先发生的记录先计算余额
    items.sort(key=lambda x: (x.record_datetime, x.id))
    
    # 计算每条记录后的现金余额
    current_balance = starting_balance
    for item in items:
        current_balance += item.amount
        item.cash_balance = current_balance
    
    # 按时间倒序排序（最新的在前），如果时间相同则按ID倒序，用于显示
    # 这样确保最新的记录显示在最上面，同一时间的记录按ID倒序（ID大的在前，因为通常是后创建的）
    items.sort(key=lambda x: (x.record_datetime, x.id), reverse=True)
    
    # 分页
    total = len(items)
    paginated_items = items[skip:skip + limit]
    
    return CashFlowListResponse(items=paginated_items, total=total)


# 创建从银行取现记录的请求模型
class CreateBankToCashRequest(BaseModel):
    """创建从银行取现记录的请求模型"""
    model_config = ConfigDict(populate_by_name=True)
    
    amount: Decimal = Field(..., description="取现金额", gt=0)
    description: Optional[str] = Field(None, description="备注说明", max_length=500)
    transfer_date: Optional[str] = Field(None, description="转账日期字符串，格式：YYYY-MM-DD HH:mm:ss，默认为当前时间")


@router.post("/bank-to-cash", response_model=dict)
def create_bank_to_cash(
    request: CreateBankToCashRequest,
    db: Session = Depends(get_db)
):
    """
    创建从银行取现记录
    从银行中取出钱放到现金中，不产生利润
    """
    from datetime import datetime, timezone, timedelta
    
    # 解析转账日期
    if request.transfer_date:
        try:
            # 解析字符串日期
            transfer_datetime = datetime.strptime(request.transfer_date, "%Y-%m-%d %H:%M:%S")
            # 如果没有时区信息，假设是本地时间（UTC+8）
            if transfer_datetime.tzinfo is None:
                china_tz = timezone(timedelta(hours=8))
                transfer_datetime = transfer_datetime.replace(tzinfo=china_tz)
        except ValueError:
            # 如果解析失败，使用当前时间
            transfer_datetime = datetime.now(timezone.utc)
    else:
        transfer_datetime = datetime.now(timezone.utc)
    
    # 创建转账记录
    transfer = CashTransfer(
        transfer_type="bank_to_cash",
        amount=request.amount,
        description=request.description or "",
        transfer_date=transfer_datetime
    )
    
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    
    return {
        "message": "从银行取现记录创建成功",
        "id": transfer.id,
        "amount": float(transfer.amount),
        "transfer_date": transfer.transfer_date.isoformat()
    }


# 创建存入银行/取现记录的请求模型
class CreateCashToBankRequest(BaseModel):
    """创建存入银行/取现记录的请求模型"""
    model_config = ConfigDict(populate_by_name=True)
    
    amount: Decimal = Field(..., description="取现金额", gt=0)
    description: Optional[str] = Field(None, description="备注说明", max_length=500)
    transfer_date: Optional[str] = Field(None, description="转账日期字符串，格式：YYYY-MM-DD HH:mm:ss，默认为当前时间")


@router.post("/cash-to-bank", response_model=dict)
def create_cash_to_bank(
    request: CreateCashToBankRequest,
    db: Session = Depends(get_db)
):
    """
    创建存入银行/取现记录
    从现金中取出钱存入银行或取走，不产生利润，单纯减少现金
    """
    from datetime import datetime, timezone, timedelta
    
    # 解析转账日期
    if request.transfer_date:
        try:
            # 解析字符串日期
            transfer_datetime = datetime.strptime(request.transfer_date, "%Y-%m-%d %H:%M:%S")
            # 如果没有时区信息，假设是本地时间（UTC+8）
            if transfer_datetime.tzinfo is None:
                china_tz = timezone(timedelta(hours=8))
                transfer_datetime = transfer_datetime.replace(tzinfo=china_tz)
        except ValueError:
            # 如果解析失败，使用当前时间
            transfer_datetime = datetime.now(timezone.utc)
    else:
        transfer_datetime = datetime.now(timezone.utc)
    
    # 创建转账记录
    transfer = CashTransfer(
        transfer_type="cash_to_bank",
        amount=request.amount,
        description=request.description or "",
        transfer_date=transfer_datetime
    )
    
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    
    return {
        "message": "取现记录创建成功",
        "id": transfer.id,
        "amount": float(transfer.amount),
        "transfer_date": transfer.transfer_date.isoformat()
    }


# 更新从银行取现记录的说明
class UpdateCashTransferDescriptionRequest(BaseModel):
    """更新现金转账记录说明的请求模型"""
    description: Optional[str] = Field(None, description="备注说明", max_length=500)


@router.put("/cash-transfer/{transfer_id}/description", response_model=dict)
def update_cash_transfer_description(
    transfer_id: int,
    request: UpdateCashTransferDescriptionRequest,
    db: Session = Depends(get_db)
):
    """
    更新现金转账记录的说明
    仅支持从银行取现类型的记录
    """
    transfer = db.query(CashTransfer).filter(CashTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="转账记录不存在")
    
    if transfer.transfer_type != "bank_to_cash":
        raise HTTPException(status_code=400, detail="仅支持更新从银行取现记录的说明")
    
    transfer.description = request.description or ""
    db.commit()
    db.refresh(transfer)
    
    return {
        "message": "说明更新成功",
        "id": transfer.id,
        "description": transfer.description
    }

