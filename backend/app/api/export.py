"""
数据导出API
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
import io
import csv
from app.db.database import get_db
from app.models.customer import Customer
from app.models.product import Product
from app.models.room import Room
from app.models.room_session import RoomSession
from app.models.customer_loan import CustomerLoan
from app.models.customer_repayment import CustomerRepayment
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord

router = APIRouter(prefix="/api/export", tags=["数据导出"])


def generate_csv(data, headers):
    """生成CSV数据"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(headers)
    
    # 写入数据
    for row in data:
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue()


@router.get("/customers")
def export_customers(db: Session = Depends(get_db)):
    """导出客户数据"""
    customers = db.query(Customer).all()
    
    headers = ["ID", "姓名", "电话", "欠款余额", "存款余额", "创建时间", "更新时间"]
    data = []
    
    for customer in customers:
        data.append([
            customer.id,
            customer.name,
            customer.phone or "",
            float(customer.balance),
            float(customer.deposit),
            customer.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            customer.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    csv_content = generate_csv(data, headers)
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=customers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.get("/sessions")
def export_sessions(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """导出房间使用记录"""
    query = db.query(RoomSession).filter(RoomSession.status == "settled")
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(RoomSession.start_time >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(RoomSession.start_time <= end_datetime)
    
    sessions = query.order_by(RoomSession.created_at.desc()).all()
    
    headers = [
        "ID", "房间ID", "房间名称", "开始时间", "结束时间", "状态",
        "台子费", "总收入", "总成本", "总利润", "创建时间"
    ]
    data = []
    
    for session in sessions:
        room = db.query(Room).filter(Room.id == session.room_id).first()
        room_name = room.name if room else ""
        
        data.append([
            session.id,
            session.room_id,
            room_name,
            session.start_time.strftime("%Y-%m-%d %H:%M:%S") if session.start_time else "",
            session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "",
            session.status,
            float(session.table_fee),
            float(session.total_revenue),
            float(session.total_cost),
            float(session.total_profit),
            session.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    csv_content = generate_csv(data, headers)
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.get("/monthly-report")
def export_monthly_report(
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份（1-12）"),
    db: Session = Depends(get_db)
):
    """导出月结清单"""
    from datetime import timedelta
    
    # 计算月份的开始和结束日期
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # 查询房间使用记录
    sessions = db.query(RoomSession).filter(
        RoomSession.start_time >= start_datetime,
        RoomSession.start_time <= end_datetime,
        RoomSession.status == "settled"
    ).order_by(RoomSession.start_time).all()
    
    headers = [
        "日期", "房间", "开始时间", "结束时间", "台子费",
        "商品收入", "商品成本", "餐费收入", "餐费成本",
        "总收入", "总成本", "总利润"
    ]
    data = []
    
    total_table_fee = Decimal("0")
    total_product_revenue = Decimal("0")
    total_product_cost = Decimal("0")
    total_meal_revenue = Decimal("0")
    total_meal_cost = Decimal("0")
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    total_profit = Decimal("0")
    
    for session in sessions:
        room = db.query(Room).filter(Room.id == session.room_id).first()
        room_name = room.name if room else ""
        
        # 查询商品消费
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session.id
        ).all()
        product_revenue = sum(c.total_price for c in consumptions)
        product_cost = sum(c.total_cost for c in consumptions)
        
        # 查询餐费
        meals = db.query(MealRecord).filter(
            MealRecord.session_id == session.id
        ).all()
        meal_revenue = sum(m.amount for m in meals)
        meal_cost = sum(m.cost_price for m in meals)
        
        session_profit = session.table_fee - product_cost - meal_cost
        
        data.append([
            session.start_time.strftime("%Y-%m-%d"),
            room_name,
            session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "",
            float(session.table_fee),
            float(product_revenue),
            float(product_cost),
            float(meal_revenue),
            float(meal_cost),
            float(session.total_revenue),
            float(session.total_cost),
            float(session_profit)
        ])
        
        total_table_fee += session.table_fee
        total_product_revenue += product_revenue
        total_product_cost += product_cost
        total_meal_revenue += meal_revenue
        total_meal_cost += meal_cost
        total_revenue += session.total_revenue
        total_cost += session.total_cost
        total_profit += session_profit
    
    # 添加汇总行
    data.append([])
    data.append([
        "合计", "", "", "", 
        float(total_table_fee),
        float(total_product_revenue),
        float(total_product_cost),
        float(total_meal_revenue),
        float(total_meal_cost),
        float(total_revenue),
        float(total_cost),
        float(total_profit)
    ])
    
    csv_content = generate_csv(data, headers)
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=monthly_report_{year}{month:02d}.csv"
        }
    )

























