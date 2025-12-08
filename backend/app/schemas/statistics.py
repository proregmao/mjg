"""
统计报表相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class RoomDetailItem(BaseModel):
    """房间详情项"""
    room_id: int
    room_name: str
    table_fee: Decimal = Field(..., description="台子费")
    session_count: int = Field(..., description="使用次数")


class TableFeeDetailItem(BaseModel):
    """台子费明细项"""
    session_id: int = Field(..., description="房间会话ID")
    room_id: int = Field(..., description="房间ID")
    room_name: str = Field(..., description="房间名称")
    table_fee: Decimal = Field(..., description="台子费")
    product_cost: Decimal = Field(..., description="商品成本")
    meal_cost: Decimal = Field(..., description="餐费成本")
    profit: Decimal = Field(..., description="利润（台子费-商品成本-餐费成本）")
    start_time: datetime = Field(..., description="开始时间")


class OtherIncomeDetailItem(BaseModel):
    """其它收入明细项"""
    id: int = Field(..., description="收入ID")
    name: str = Field(..., description="收入名称")
    amount: Decimal = Field(..., description="收入金额")
    payment_method: str = Field(..., description="支付方式")
    income_date: datetime = Field(..., description="收入日期")
    description: Optional[str] = Field(None, description="备注说明")


class OtherExpenseDetailItem(BaseModel):
    """其它支出明细项"""
    id: int = Field(..., description="支出ID")
    name: str = Field(..., description="支出名称")
    amount: Decimal = Field(..., description="支出金额")
    payment_method: str = Field(..., description="支付方式")
    expense_date: datetime = Field(..., description="支出日期")
    description: Optional[str] = Field(None, description="备注说明")


class CostDetailItem(BaseModel):
    """成本明细项"""
    cost_type: str = Field(..., description="成本类型：product_cost, meal_cost")
    cost_name: str = Field(..., description="成本名称")
    amount: Decimal = Field(..., description="金额")


class CustomerFinancialItem(BaseModel):
    """客户财务项"""
    customer_id: int
    customer_name: str
    loan_amount: Decimal = Field(..., description="借款金额")
    repayment_amount: Decimal = Field(..., description="还款金额")
    current_balance: Decimal = Field(..., description="当前余额（负数=欠款，正数=预存）")


class DailyStatisticsResponse(BaseModel):
    """每日统计响应模型"""
    date: date
    total_revenue: Decimal = Field(..., description="总收入")
    total_cost: Decimal = Field(..., description="总成本")
    total_profit: Decimal = Field(..., description="总利润")
    table_fee_total: Decimal = Field(..., description="台子费总额")
    table_fee_profit: Decimal = Field(..., description="台子费利润（台子费-商品成本-餐费成本）")
    product_revenue: Decimal = Field(..., description="商品收入")
    product_cost: Decimal = Field(..., description="商品成本")
    meal_revenue: Decimal = Field(..., description="餐费收入")
    meal_cost: Decimal = Field(..., description="餐费成本")
    other_income: Decimal = Field(default=0, description="其它收入")
    other_expense: Decimal = Field(default=0, description="其它支出")
    session_count: int = Field(..., description="房间使用次数")
    room_count: int = Field(..., description="使用房间数")
    # 详细信息
    room_details: List[RoomDetailItem] = Field(default_factory=list, description="房间使用详情")
    cost_details: List[CostDetailItem] = Field(default_factory=list, description="成本明细")
    customer_financials: List[CustomerFinancialItem] = Field(default_factory=list, description="客户财务详情")
    table_fee_details: List[TableFeeDetailItem] = Field(default_factory=list, description="台子费明细清单")
    other_income_details: List[OtherIncomeDetailItem] = Field(default_factory=list, description="其它收入明细清单")
    other_expense_details: List[OtherExpenseDetailItem] = Field(default_factory=list, description="其它支出明细清单")


class MonthlyStatisticsResponse(BaseModel):
    """每月统计响应模型"""
    year: int
    month: int
    total_revenue: Decimal = Field(..., description="总收入")
    total_cost: Decimal = Field(..., description="总成本")
    total_profit: Decimal = Field(..., description="总利润")
    other_income: Decimal = Field(default=0, description="其它收入")
    other_expense: Decimal = Field(default=0, description="其它支出")
    table_fee_total: Decimal = Field(..., description="台子费总额")
    table_fee_profit: Decimal = Field(..., description="台子费利润（台子费-商品成本-餐费成本）")
    product_revenue: Decimal = Field(..., description="商品收入")
    product_cost: Decimal = Field(..., description="商品成本")
    meal_revenue: Decimal = Field(..., description="餐费收入")
    meal_cost: Decimal = Field(..., description="餐费成本")
    session_count: int = Field(..., description="房间使用次数")
    room_count: int = Field(..., description="使用房间数")
    daily_statistics: List[DailyStatisticsResponse] = Field(default_factory=list, description="每日明细")
    table_fee_details: List[TableFeeDetailItem] = Field(default_factory=list, description="台子费明细清单（全月）")
    other_income_details: List[OtherIncomeDetailItem] = Field(default_factory=list, description="其它收入明细清单（全月）")
    other_expense_details: List[OtherExpenseDetailItem] = Field(default_factory=list, description="其它支出明细清单（全月）")


class CustomerRankingItem(BaseModel):
    """客户排行项"""
    customer_id: int
    customer_name: str
    total_consumption: Decimal = Field(..., description="总消费金额")
    total_loans: Decimal = Field(..., description="总借款金额")
    current_balance: Decimal = Field(..., description="当前欠款余额")
    session_count: int = Field(..., description="参与房间使用次数")


class RoomUsageItem(BaseModel):
    """房间使用率项"""
    room_id: int
    room_name: str
    session_count: int = Field(..., description="使用次数")
    total_hours: Decimal = Field(..., description="总使用时长（小时）")
    total_revenue: Decimal = Field(..., description="总收入")
    total_profit: Decimal = Field(..., description="总利润")


class ProductSalesItem(BaseModel):
    """商品销售统计项"""
    product_id: int
    product_name: str
    total_quantity: int = Field(..., description="总销售数量")
    total_revenue: Decimal = Field(..., description="总收入")
    total_cost: Decimal = Field(..., description="总成本")
    total_profit: Decimal = Field(..., description="总利润")













