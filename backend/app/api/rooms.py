"""
房间管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from app.db.database import get_db
from app.models.room import Room
from app.models.room_session import RoomSession
from app.models.room_customer import RoomCustomer
from app.models.customer import Customer
from app.models.product import Product
from app.models.customer_loan import CustomerLoan
from app.models.customer_repayment import CustomerRepayment
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord
from app.models.room_transfer import RoomTransfer
from app.models.session_result import SessionResult
from app.schemas.room import (
    RoomCreate, RoomUpdate, RoomResponse, RoomSessionResponse,
    StartSessionRequest, AddCustomerRequest, RecordLoanRequest,
    RecordRepaymentRequest, RecordProductRequest, RecordMealRequest, 
    TransferRoomRequest, SetTableFeeRequest,
    UpdateProductConsumptionRequest, UpdateMealRecordRequest,
    UpdateLoanRequest, UpdateRepaymentRequest, SettleSessionRequest
)
from app.schemas.room_detail import RoomSessionDetailResponse

router = APIRouter(prefix="/api/rooms", tags=["房间管理"])


@router.get("", response_model=List[RoomResponse])
def get_rooms(db: Session = Depends(get_db)):
    """获取房间列表"""
    rooms = db.query(Room).all()
    return rooms


@router.post("", response_model=RoomResponse)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    """创建房间"""
    db_room = Room(**room.dict())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    request: RoomUpdate,
    db: Session = Depends(get_db)
):
    """更新房间"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查名称是否重复
    if request.name and request.name != room.name:
        existing_room = db.query(Room).filter(Room.name == request.name).first()
        if existing_room:
            raise HTTPException(status_code=400, detail="房间名称已存在")
        room.name = request.name
    
    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db)
):
    """
    删除房间
    注意：只能删除从未被使用过的房间（没有关联的RoomSession记录）
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查房间是否有使用记录（无论是否结算）
    session_count = db.query(RoomSession).filter(RoomSession.room_id == room_id).count()
    if session_count > 0:
        raise HTTPException(
            status_code=400, 
            detail="该房间已有使用记录，为保证财务数据完整，无法删除。建议将其更名以作区分。"
        )
    
    try:
        db.delete(room)
        db.commit()
        return {"message": f"房间 {room.name} 已删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")



@router.post("/{room_id}/start-session", response_model=RoomSessionResponse)
def start_session(
    room_id: int,
    db: Session = Depends(get_db)
):
    """开始使用房间"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    if room.status != "idle":
        raise HTTPException(status_code=400, detail="房间正在使用中，无法开始新的使用")
    
    # 创建房间使用记录
    session = RoomSession(
        room_id=room_id,
        start_time=datetime.now(timezone.utc),
        status="in_progress"
    )
    db.add(session)
    
    # 更新房间状态
    room.status = "in_use"
    
    db.commit()
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/add-customer")
def add_customer_to_session(
    session_id: int,
    request: AddCustomerRequest,
    db: Session = Depends(get_db)
):
    """添加客户到房间"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="房间使用已结束，无法添加客户")
    
    customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 检查客户是否已在房间中
    existing = db.query(RoomCustomer).filter(
        RoomCustomer.session_id == session_id,
        RoomCustomer.customer_id == request.customer_id,
        RoomCustomer.left_at.is_(None)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="客户已在房间中")
    
    # 添加客户
    room_customer = RoomCustomer(
        session_id=session_id,
        customer_id=request.customer_id,
        joined_at=datetime.now(timezone.utc)
    )
    db.add(room_customer)
    db.commit()
    
    return {"message": "客户已添加到房间"}


@router.post("/sessions/{session_id}/remove-customer")
def remove_customer_from_session(
    session_id: int,
    customer_id: int,
    db: Session = Depends(get_db)
):
    """移除房间客户（中途离开）"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    room_customer = db.query(RoomCustomer).filter(
        RoomCustomer.session_id == session_id,
        RoomCustomer.customer_id == customer_id,
        RoomCustomer.left_at.is_(None)
    ).first()
    
    if not room_customer:
        raise HTTPException(status_code=404, detail="客户不在房间中")
    
    room_customer.left_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "客户已从房间移除"}


@router.post("/sessions/{session_id}/loan")
def record_loan(
    session_id: int,
    request: RecordLoanRequest,
    db: Session = Depends(get_db)
):
    """记录借款"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    # 允许在已结算的房间中记录借款（用于补充记录）
    # if session.status != "in_progress":
    #     raise HTTPException(status_code=400, detail="房间使用已结束，无法记录借款")
    
    customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 生成说明
    description = f"向麻将馆借款 - 剩余未还: ¥{request.amount:.2f} - 正常"
    
    # 创建借款记录
    loan = CustomerLoan(
        customer_id=request.customer_id,
        amount=request.amount,
        loan_type="from_shop",
        status="active",
        remaining_amount=request.amount,
        payment_method=request.payment_method or "现金",  # 默认现金
        description=description,
        session_id=session_id
    )
    db.add(loan)
    
    # 更新客户总帐：借款减少balance（增加欠款或减少预存）
    # balance负数=欠款，正数=预存，借款应该减少balance
    customer.balance = customer.balance - request.amount
    
    db.commit()
    db.refresh(loan)
    return {"message": "借款记录已创建", "loan_id": loan.id}


@router.put("/sessions/{session_id}/loan/{loan_id}")
def update_loan_record(
    session_id: int,
    loan_id: int,
    request: UpdateLoanRequest,
    db: Session = Depends(get_db)
):
    """更新借款记录"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    loan = db.query(CustomerLoan).filter(
        CustomerLoan.id == loan_id,
        CustomerLoan.session_id == session_id
    ).first()
    if not loan:
        raise HTTPException(status_code=404, detail="借款记录不存在")

    customer = db.query(Customer).filter(Customer.id == loan.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    try:
        # 1. 更新客户余额
        # 计算差额：新金额 - 旧金额
        # 借款增加 -> balance减少
        delta_amount = request.amount - loan.amount
        customer.balance = customer.balance - delta_amount

        # 2. 更新借款记录
        loan.amount = request.amount
        if request.payment_method:
            loan.payment_method = request.payment_method
            
        # 3. 重新计算剩余金额
        # 获取所有关联的还款总额
        from sqlalchemy import func
        repaid_sum = db.query(func.sum(CustomerRepayment.amount)).filter(
            CustomerRepayment.loan_id == loan.id
        ).scalar() or 0
        repaid_sum = Decimal(str(repaid_sum))
        
        # 剩余金额 = 总借款 - 已还款
        # 如果还款超过借款，remaining_amount 为 0 (超出的部分已经在还款时冲抵了总欠款，这里只关注此笔借款的结清状态)
        # 注意：这里的逻辑简化了，因为还款时如果extra_repay > 0，那部分其实不属于loan_id的repayment (在代码逻辑中拆分了?)
        # 检查 record_repayment 逻辑: 
        # 当还款超出时，并没有拆分记录，只是 repayment.amount 记了总数? 
        # 不，record_repayment中: 
        # if repay_amount > remaining_amount: 
        #    repayment关联了loan_id，amount是repay_amount(总还款).
        # 所以 sum(repayment.amount) 可能会超过 loan.amount
        
        loan.remaining_amount = max(Decimal('0'), loan.amount - repaid_sum)
        
        # 4. 更新借款状态
        if loan.remaining_amount <= 0:
            loan.status = "repaid"
        else:
            loan.status = "active"

        db.commit()
        db.refresh(loan)
        return {"message": "借款记录已更新", "loan_id": loan.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/sessions/{session_id}/repayment")
def record_repayment(
    session_id: int,
    request: RecordRepaymentRequest,
    db: Session = Depends(get_db)
):
    """
    记录还款
    - 如果提供了 loan_id，还款金额可以超过借款金额，超出部分将冲抵客户的总欠款余额
    - 如果没有提供 loan_id，直接冲抵客户的总欠款余额
    """
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    # 获取客户
    customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    repay_amount = Decimal(str(request.amount))
    is_refund = repay_amount < 0  # 负数表示退款/支付给客户
    abs_amount = abs(repay_amount)
    
    # 如果是退款（负数），直接更新balance，不处理借款记录
    if is_refund:
        # 负数：退款/支付给客户（减少balance，可能增加欠款或减少预存）
        customer.balance = customer.balance + repay_amount  # repay_amount是负数，所以是减少
        
        # 如果余额为正，更新deposit
        if customer.balance > 0:
            customer.deposit = customer.balance
        else:
            customer.deposit = Decimal('0')
        
        # 生成说明（负数表示退款）
        payment_method = request.payment_method or "现金"
        description = f"退款/支付给客户 ({payment_method})"
        
        # 创建还款记录（负数）
        repayment = CustomerRepayment(
            customer_id=request.customer_id,
            loan_id=None,  # 退款不关联借款记录
            amount=repay_amount,  # 负数
            payment_method=payment_method,
            description=description,
            session_id=session_id
        )
        db.add(repayment)
        db.commit()
        
        return {
            "message": f"退款成功，已向客户支付 ¥{abs_amount:.2f}",
            "repayment_id": repayment.id,
            "loan_repay": 0.0,
            "extra_repay": float(repay_amount),
            "customer_balance": float(customer.balance)
        }
    
    # 正数：正常还款逻辑
    # 如果有借款记录，处理借款还款
    if request.loan_id:
        # 获取借款记录
        loan = db.query(CustomerLoan).filter(CustomerLoan.id == request.loan_id).first()
        if not loan:
            raise HTTPException(status_code=404, detail="借款记录不存在")
        
        if loan.customer_id != request.customer_id:
            raise HTTPException(status_code=400, detail="借款记录与客户不匹配")
        
        remaining_amount = Decimal(str(loan.remaining_amount))
        
        # 计算还款金额中用于还此笔借款的部分和超出的部分
        if repay_amount <= remaining_amount:
            # 还款金额小于等于剩余借款金额，全部用于还此笔借款
            loan_repay = repay_amount
            extra_repay = Decimal('0')
        else:
            # 还款金额大于剩余借款金额，超出部分冲抵总欠款
            loan_repay = remaining_amount
            extra_repay = repay_amount - remaining_amount
        
        # 生成说明
        payment_method = request.payment_method or "现金"
        description = f"还款 - 关联借款ID: {loan.id} ({payment_method})"
        
        # 创建还款记录
        repayment = CustomerRepayment(
            customer_id=request.customer_id,
            loan_id=loan.id,
            amount=repay_amount,  # 记录实际还款总额
            payment_method=payment_method,
            description=description,
            session_id=session_id
        )
        db.add(repayment)
        
        # 更新借款状态
        loan.remaining_amount = max(Decimal('0'), loan.remaining_amount - loan_repay)
        if loan.remaining_amount <= 0:
            loan.status = "repaid"
        
        # 更新客户总帐：还款增加balance（减少欠款或增加预存）
        # balance负数=欠款，正数=预存，还款应该增加balance
        customer.balance = customer.balance + repay_amount
        
        db.commit()
        
        result = {
            "message": "还款成功",
            "repayment_id": repayment.id,
            "loan_repay": float(loan_repay),
            "extra_repay": float(extra_repay),
            "customer_balance": float(customer.balance)
        }
        
        if extra_repay > 0:
            result["message"] = f"还款成功，其中 ¥{loan_repay:.2f} 用于还清此笔借款，¥{extra_repay:.2f} 已冲抵总欠款"
        
        return result
    else:
        # 没有指定借款记录，先查找客户是否有未还清的借款记录（按时间排序，优先还最早的）
        active_loan = db.query(CustomerLoan).filter(
            CustomerLoan.customer_id == request.customer_id,
            CustomerLoan.status == "active",
            CustomerLoan.remaining_amount > 0
        ).order_by(CustomerLoan.created_at.asc()).first()
        
        if active_loan:
            # 有未还清的借款记录，先还借款
            loan_amount = Decimal(str(active_loan.amount))
            remaining_amount = Decimal(str(active_loan.remaining_amount))
            
            # 计算还款金额中用于还此笔借款的部分和超出的部分
            if repay_amount <= remaining_amount:
                # 还款金额小于等于剩余借款金额，全部用于还此笔借款
                loan_repay = repay_amount
                extra_repay = Decimal('0')
            else:
                # 还款金额大于剩余借款金额，超出部分冲抵总欠款
                loan_repay = remaining_amount
                extra_repay = repay_amount - remaining_amount
            
            # 生成说明
            payment_method = request.payment_method or "现金"
            description = f"还款 - 关联借款ID: {active_loan.id} ({payment_method})"
            
            # 创建还款记录
            repayment = CustomerRepayment(
                customer_id=request.customer_id,
                loan_id=active_loan.id,
                amount=repay_amount,  # 记录实际还款总额
                payment_method=payment_method,
                description=description,
                session_id=session_id
            )
            db.add(repayment)
            
            # 更新借款状态
            active_loan.remaining_amount = max(Decimal('0'), active_loan.remaining_amount - loan_repay)
            if active_loan.remaining_amount <= 0:
                active_loan.status = "repaid"
            
            # 更新客户总帐：还款增加balance（减少欠款或增加预存）
            # balance负数=欠款，正数=预存，还款应该增加balance
            customer.balance = customer.balance + repay_amount
            
            db.commit()
            
            result = {
                "message": "还款成功",
                "repayment_id": repayment.id,
                "loan_repay": float(loan_repay),
                "extra_repay": float(extra_repay),
                "customer_balance": float(customer.balance)
            }
            
            if extra_repay > 0:
                result["message"] = f"还款成功，其中 ¥{loan_repay:.2f} 用于还清此笔借款，¥{extra_repay:.2f} 已冲抵总欠款"
            
            return result
        else:
            # 生成说明
            payment_method = request.payment_method or "现金"
            description = f"还款 - 还总欠款 ({payment_method})"
            
            # 没有借款记录，直接更新总帐
            repayment = CustomerRepayment(
                customer_id=request.customer_id,
                loan_id=None,  # 不关联借款记录
                amount=repay_amount,
                payment_method=payment_method,
                description=description,
                session_id=session_id
            )
            db.add(repayment)
            
            # 更新客户总帐：还款增加balance（减少欠款或增加预存）
            # balance负数=欠款，正数=预存，还款应该增加balance
            customer.balance = customer.balance + repay_amount
            
            db.commit()
            
            return {
                "message": f"还款成功，¥{repay_amount:.2f} 已冲抵总欠款",
                "repayment_id": repayment.id,
                "loan_repay": 0.0,
                "extra_repay": float(repay_amount),
                "customer_balance": float(customer.balance)
            }


@router.put("/sessions/{session_id}/repayment/{repayment_id}")
def update_repayment_record(
    session_id: int,
    repayment_id: int,
    request: UpdateRepaymentRequest,
    db: Session = Depends(get_db)
):
    """更新还款记录"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    repayment = db.query(CustomerRepayment).filter(
        CustomerRepayment.id == repayment_id,
        CustomerRepayment.session_id == session_id
    ).first()
    if not repayment:
        raise HTTPException(status_code=404, detail="还款记录不存在")

    customer = db.query(Customer).filter(Customer.id == repayment.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    try:
        # 1. 更新客户余额
        # 计算差额：新金额 - 旧金额
        # 还款增加 -> balance增加
        delta_amount = request.amount - repayment.amount
        customer.balance = customer.balance + delta_amount
        
        # 更新deposit (如果balance > 0)
        if customer.balance > 0:
            customer.deposit = customer.balance
        else:
            customer.deposit = Decimal('0')

        # 2. 更新还款记录
        repayment.amount = request.amount
        if request.payment_method:
            repayment.payment_method = request.payment_method

        # 3. 如果关联了借款，需要更新借款状态
        if repayment.loan_id:
            loan = db.query(CustomerLoan).filter(CustomerLoan.id == repayment.loan_id).first()
            if loan:
                # 重新计算剩余金额
                from sqlalchemy import func
                # 注意：此时repayment已经是更新后的金额（因为flush了? 没有flush，只是python对象更新了）
                # SQLAlchemy session中，如果对象已修改但未commit，query可能查到旧值，除非flush
                # 这里为了保险，手动计算：sum(others) + new_amount
                
                # option 1: flush first
                db.flush()
                
                repaid_sum = db.query(func.sum(CustomerRepayment.amount)).filter(
                    CustomerRepayment.loan_id == loan.id
                ).scalar() or 0
                repaid_sum = Decimal(str(repaid_sum))
                
                loan.remaining_amount = max(Decimal('0'), loan.amount - repaid_sum)
                
                # 更新状态
                if loan.remaining_amount <= 0:
                    loan.status = "repaid"
                else:
                    loan.status = "active"

        db.commit()
        db.refresh(repayment)
        return {"message": "还款记录已更新", "repayment_id": repayment.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/sessions/{session_id}/product")
def record_product(
    session_id: int,
    request: RecordProductRequest,
    db: Session = Depends(get_db)
):
    """记录商品消费"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    # 允许在已结算的房间中记录商品消费（用于补充记录）
    # if session.status != "in_progress":
    #     raise HTTPException(status_code=400, detail="房间使用已结束，无法记录消费")
    
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    if not product.is_active:
        raise HTTPException(status_code=400, detail="商品已禁用")
    
    if product.product_type == "meal":
        raise HTTPException(status_code=400, detail="请使用餐费记录接口")
    
    # 允许负库存，不检查库存限制
    
    # 计算总价和总成本
    total_price = product.price * request.quantity
    total_cost = product.cost_price * request.quantity
    
    # 创建消费记录
    consumption = ProductConsumption(
        session_id=session_id,
        customer_id=request.customer_id,
        product_id=request.product_id,
        quantity=request.quantity,
        unit_price=product.price,
        total_price=total_price,
        cost_price=product.cost_price,
        total_cost=total_cost,
        payment_method=request.payment_method or "现金"  # 默认现金
    )
    db.add(consumption)
    
    # 更新库存
    product.stock = product.stock - request.quantity
    
    # 更新房间使用记录的成本（收入即台子费，不再单独加商品收入）
    session.total_cost = session.total_cost + total_cost
    
    db.commit()
    db.refresh(consumption)
    return {"message": "商品消费已记录", "consumption_id": consumption.id}


@router.post("/sessions/{session_id}/meal")
def record_meal(
    session_id: int,
    request: RecordMealRequest,
    db: Session = Depends(get_db)
):
    """记录餐费"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    # 允许在已结算的房间中记录餐费（用于补充记录）
    # if session.status != "in_progress":
    #     raise HTTPException(status_code=400, detail="房间使用已结束，无法记录餐费")
    
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="餐费商品不存在")
    
    if product.product_type != "meal":
        raise HTTPException(status_code=400, detail="该商品不是餐费类型")
    
    # 创建餐费记录
    # 餐费的成本价等于餐费金额本身，因为餐费是实际支出的费用
    # 餐费金额会变动（这顿100，下顿可能是200），所以成本应该等于当次餐费金额
    meal_record = MealRecord(
        session_id=session_id,
        customer_id=request.customer_id,
        product_id=request.product_id,
        amount=request.amount,
        cost_price=request.amount,  # 餐费成本 = 餐费金额（餐费本身就是成本）
        payment_method=request.payment_method or "现金",  # 默认现金
        description=request.description
    )
    db.add(meal_record)
    
    # 更新房间使用记录的成本（收入即台子费，不再单独加餐费收入）
    session.total_cost = session.total_cost + request.amount  # 餐费成本 = 餐费金额
    
    db.commit()
    db.refresh(meal_record)
    return {"message": "餐费已记录", "meal_record_id": meal_record.id}


@router.put("/sessions/{session_id}/product/{consumption_id}")
def update_product_consumption(
    session_id: int,
    consumption_id: int,
    request: UpdateProductConsumptionRequest,
    db: Session = Depends(get_db)
):
    """更新商品消费数量"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    consumption = db.query(ProductConsumption).filter(
        ProductConsumption.id == consumption_id,
        ProductConsumption.session_id == session_id
    ).first()
    if not consumption:
        raise HTTPException(status_code=404, detail="商品消费记录不存在")
    
    try:
        # 获取商品信息
        product = db.query(Product).filter(Product.id == consumption.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        
        # 计算数量差异
        quantity_diff = request.quantity - consumption.quantity
        
        # 更新库存（如果数量增加，减少库存；如果数量减少，增加库存）
        product.stock = product.stock - quantity_diff
        
        # 更新成本
        session.total_cost = session.total_cost - consumption.total_cost
        
        # 计算新的总价和总成本
        new_total_price = product.price * request.quantity
        new_total_cost = product.cost_price * request.quantity
        
        # 更新消费记录
        consumption.quantity = request.quantity
        consumption.total_price = new_total_price
        consumption.total_cost = new_total_cost
        
        # 更新成本
        session.total_cost = session.total_cost + new_total_cost
        
        db.commit()
        db.refresh(consumption)
        return {"message": "商品消费记录已更新", "consumption_id": consumption.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/sessions/{session_id}/product/{consumption_id}")
def delete_product_consumption(
    session_id: int,
    consumption_id: int,
    db: Session = Depends(get_db)
):
    """删除商品消费记录"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    consumption = db.query(ProductConsumption).filter(
        ProductConsumption.id == consumption_id,
        ProductConsumption.session_id == session_id
    ).first()
    if not consumption:
        raise HTTPException(status_code=404, detail="商品消费记录不存在")
    
    try:
        # 获取商品信息
        product = db.query(Product).filter(Product.id == consumption.product_id).first()
        if product:
            # 恢复库存
            product.stock = product.stock + consumption.quantity
        
        # 回滚房间使用记录的成本
        session.total_cost = session.total_cost - consumption.total_cost
        
        # 删除消费记录
        db.delete(consumption)
        
        db.commit()
        return {"message": "商品消费记录已删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.put("/sessions/{session_id}/meal/{meal_record_id}")
def update_meal_record(
    session_id: int,
    meal_record_id: int,
    request: UpdateMealRecordRequest,
    db: Session = Depends(get_db)
):
    """更新餐费金额"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    meal_record = db.query(MealRecord).filter(
        MealRecord.id == meal_record_id,
        MealRecord.session_id == session_id
    ).first()
    if not meal_record:
        raise HTTPException(status_code=404, detail="餐费记录不存在")
    
    try:
        # 回滚旧的成本（餐费的成本等于餐费金额本身）
        session.total_cost = session.total_cost - meal_record.amount
        
        # 更新餐费记录
        meal_record.amount = request.amount
        meal_record.cost_price = request.amount  # 餐费成本 = 餐费金额
        
        # 更新房间使用记录的成本
        session.total_cost = session.total_cost + request.amount
        
        db.commit()
        db.refresh(meal_record)
        return {"message": "餐费记录已更新", "meal_record_id": meal_record.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/sessions/{session_id}/meal/{meal_record_id}")
def delete_meal_record(
    session_id: int,
    meal_record_id: int,
    db: Session = Depends(get_db)
):
    """删除餐费记录"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    meal_record = db.query(MealRecord).filter(
        MealRecord.id == meal_record_id,
        MealRecord.session_id == session_id
    ).first()
    if not meal_record:
        raise HTTPException(status_code=404, detail="餐费记录不存在")
    
    try:
        # 回滚房间使用记录的成本
        # 餐费的成本等于餐费金额本身
        session.total_cost = session.total_cost - meal_record.amount
        
        # 删除餐费记录
        db.delete(meal_record)
        
        db.commit()
        return {"message": "餐费记录已删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/sessions/{session_id}/transfer-room")
def transfer_room(
    session_id: int,
    request: TransferRoomRequest,
    db: Session = Depends(get_db)
):
    """房间转移"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="房间使用已结束，无法转移")
    
    to_room = db.query(Room).filter(Room.id == request.to_room_id).first()
    if not to_room:
        raise HTTPException(status_code=404, detail="目标房间不存在")
    
    if to_room.status != "idle":
        raise HTTPException(status_code=400, detail="目标房间正在使用中")
    
    from_room = db.query(Room).filter(Room.id == session.room_id).first()
    
    # 创建转移记录
    transfer = RoomTransfer(
        session_id=session_id,
        from_room_id=session.room_id,
        to_room_id=request.to_room_id,
        transferred_at=datetime.now(timezone.utc)
    )
    db.add(transfer)
    
    # 更新房间使用记录的房间ID
    session.room_id = request.to_room_id
    
    # 更新房间状态
    from_room.status = "idle"
    to_room.status = "in_use"
    
    db.commit()
    return {"message": "房间转移成功"}


@router.put("/sessions/{session_id}/table-fee")
def set_table_fee(
    session_id: int,
    request: SetTableFeeRequest,
    db: Session = Depends(get_db)
):
    """设置台子费"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="房间使用已结束，无法设置台子费")
    
    # 更新台子费，并强制同步总收入（台子费 = 总收入）
    session.table_fee = request.table_fee
    session.table_fee_payment_method = request.payment_method or "现金"  # 默认现金
    session.total_revenue = request.table_fee
    
    db.commit()
    db.refresh(session)
    return {"message": "台子费已设置"}


@router.post("/sessions/{session_id}/settle")
def settle_session(
    session_id: int,
    request: SettleSessionRequest = None,
    db: Session = Depends(get_db)
):
    """结算房间"""
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="房间使用已结算")
    
    # 计算利润 = 总收入 - 总成本
    session.total_profit = session.total_revenue - session.total_cost
    
    # 更新房间使用记录
    session.status = "settled"
    session.end_time = datetime.now(timezone.utc)
    
    # 更新房间状态
    room = db.query(Room).filter(Room.id == session.room_id).first()
    if room:
        room.status = "idle"
    
    # 保存客户输赢结果
    if request and request.customer_results:
        for result in request.customer_results:
            session_result = SessionResult(
                session_id=session.id,
                customer_id=result.customer_id,
                net_win_loss=result.net_win_loss
            )
            db.add(session_result)

    db.commit()
    db.refresh(session)
    return {
        "message": "房间结算成功",
        "total_profit": float(session.total_profit),
        "session": session
    }


@router.get("/sessions", response_model=List[RoomSessionResponse])
def get_sessions(
    skip: int = 0,
    limit: int = 100,
    room_id: Optional[int] = None,
    status: Optional[str] = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """获取房间使用记录"""
    query = db.query(RoomSession)
    
    # 默认不显示已删除的记录
    if not include_deleted:
        query = query.filter(RoomSession.deleted_at.is_(None))
    
    if room_id:
        query = query.filter(RoomSession.room_id == room_id)
    
    if status:
        query = query.filter(RoomSession.status == status)
    
    sessions = query.order_by(RoomSession.created_at.desc()).offset(skip).limit(limit).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=RoomSessionDetailResponse)
def get_session(session_id: int, include_deleted: bool = False, db: Session = Depends(get_db)):
    """获取房间使用记录详情（包含关联数据）"""
    from app.schemas.room_detail import (
        RoomCustomerDetail,
        LoanDetail,
        RepaymentDetail,
        ProductConsumptionDetail,
        MealRecordDetail,
    )
    
    query = db.query(RoomSession).filter(RoomSession.id == session_id)
    if not include_deleted:
        query = query.filter(RoomSession.deleted_at.is_(None))
    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    room = db.query(Room).filter(Room.id == session.room_id).first()
    
    # 获取客户列表
    room_customers = db.query(RoomCustomer).filter(
        RoomCustomer.session_id == session_id
    ).all()
    customers = []
    for rc in room_customers:
        customer = db.query(Customer).filter(Customer.id == rc.customer_id).first()
        if customer:
            customers.append(RoomCustomerDetail(
                id=rc.id,
                customer_id=customer.id,
                customer_name=customer.name,
                customer_phone=customer.phone,
                joined_at=rc.joined_at,
                left_at=rc.left_at
            ))
    
    # 获取借款记录
    loans = db.query(CustomerLoan).filter(
        CustomerLoan.session_id == session_id
    ).all()
    loan_details = []
    for loan in loans:
        customer = db.query(Customer).filter(Customer.id == loan.customer_id).first()
        if customer:
            loan_details.append(LoanDetail(
                id=loan.id,
                customer_id=customer.id,
                customer_name=customer.name,
                amount=loan.amount,
                remaining_amount=loan.remaining_amount,
                payment_method=loan.payment_method,
                description=loan.description,
                created_at=loan.created_at
            ))
    
    # 获取还款记录
    repayments = db.query(CustomerRepayment).filter(
        CustomerRepayment.session_id == session_id
    ).all()
    repayment_details = []
    for repayment in repayments:
        customer = db.query(Customer).filter(Customer.id == repayment.customer_id).first()
        # 即使客户不存在，也返回还款记录（使用客户ID作为名称）
        customer_name = customer.name if customer else f"客户ID:{repayment.customer_id}"
        repayment_details.append(RepaymentDetail(
            id=repayment.id,
            customer_id=repayment.customer_id,
            customer_name=customer_name,
            loan_id=repayment.loan_id,
            amount=repayment.amount,
            payment_method=repayment.payment_method,
            description=repayment.description,
            created_at=repayment.created_at
        ))
    
    # 获取商品消费记录
    consumptions = db.query(ProductConsumption).filter(
        ProductConsumption.session_id == session_id
    ).all()
    consumption_details = []
    for consumption in consumptions:
        product = db.query(Product).filter(Product.id == consumption.product_id).first()
        customer_name = None
        if consumption.customer_id:
            customer = db.query(Customer).filter(Customer.id == consumption.customer_id).first()
            if customer:
                customer_name = customer.name
        consumption_details.append(ProductConsumptionDetail(
            id=consumption.id,
            product_id=consumption.product_id,
            product_name=product.name if product else "",
            customer_id=consumption.customer_id,
            customer_name=customer_name,
            quantity=consumption.quantity,
            unit_price=consumption.unit_price,
            total_price=consumption.total_price,
            payment_method=consumption.payment_method,
            created_at=consumption.created_at
        ))
    
    # 获取餐费记录
    meals = db.query(MealRecord).filter(
        MealRecord.session_id == session_id
    ).all()
    meal_details = []
    for meal in meals:
        product = db.query(Product).filter(Product.id == meal.product_id).first()
        customer_name = None
        if meal.customer_id:
            customer = db.query(Customer).filter(Customer.id == meal.customer_id).first()
            if customer:
                customer_name = customer.name
        meal_details.append(MealRecordDetail(
            id=meal.id,
            product_id=meal.product_id,
            product_name=product.name if product else "",
            customer_id=meal.customer_id,
            customer_name=customer_name,
            amount=meal.amount,
            description=meal.description,
            payment_method=meal.payment_method,
            created_at=meal.created_at
        ))
    
    response = RoomSessionDetailResponse(
        id=session.id,
        room_id=session.room_id,
        room_name=room.name if room else "",
        start_time=session.start_time,
        end_time=session.end_time,
        status=session.status,
        table_fee=session.table_fee,
        table_fee_payment_method=session.table_fee_payment_method,
        total_revenue=session.total_revenue,
        total_cost=session.total_cost,
        total_profit=session.total_profit,
        created_at=session.created_at,
        updated_at=session.updated_at,
        customers=customers,
        loans=loan_details,
        repayments=repayment_details,
        product_consumptions=consumption_details,
        meal_records=meal_details
    )
    
    # 调试：打印响应数据
    print(f"[DEBUG] Session {session_id} - repayments count: {len(repayment_details)}")
    print(f"[DEBUG] Response repayments: {len(response.repayments)}")
    
    return response


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    删除指定的房间使用记录
    
    功能说明：
    - 删除指定的房间使用记录（必须是已结算状态）
    - 回滚所有相关的财务数据（客户余额、库存等）
    - 删除所有关联记录（客户关联、借款、还款、商品消费、餐费记录、房间转移记录）
    - 删除房间使用记录本身
    - 更新房间状态为idle（如果删除的是最后一次记录）
    """
    # 查找房间使用记录
    session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在")
    
    # 只允许删除已结算的记录
    if session.status != "settled":
        raise HTTPException(status_code=400, detail="只能删除已结算的使用记录")
    
    room_id = session.room_id
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    try:
        # 1. 回滚客户余额（处理借款和还款）
        # 获取所有借款记录
        loans = db.query(CustomerLoan).filter(
            CustomerLoan.session_id == session_id
        ).all()
        for loan in loans:
            customer = db.query(Customer).filter(Customer.id == loan.customer_id).first()
            if customer:
                # 借款时减少了balance（增加欠款），删除时需要增加balance（减少欠款）
                customer.balance = customer.balance + loan.amount
                # 恢复借款记录状态
                loan.status = "active"
                loan.remaining_amount = loan.amount
        
        # 获取所有还款记录
        repayments = db.query(CustomerRepayment).filter(
            CustomerRepayment.session_id == session_id
        ).all()
        for repayment in repayments:
            customer = db.query(Customer).filter(Customer.id == repayment.customer_id).first()
            if customer:
                # 还款时增加了balance（减少欠款），删除时需要减少balance（增加欠款）
                customer.balance = customer.balance - repayment.amount
                
                # 如果有关联的借款记录，需要恢复借款状态
                if repayment.loan_id:
                    loan = db.query(CustomerLoan).filter(CustomerLoan.id == repayment.loan_id).first()
                    if loan:
                        # 恢复借款的剩余金额
                        loan.remaining_amount = loan.remaining_amount + repayment.amount
                        # 如果还款金额大于等于借款金额，借款状态恢复为active
                        if loan.remaining_amount > 0:
                            loan.status = "active"
        
        # 2. 恢复商品库存
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session_id
        ).all()
        for consumption in consumptions:
            product = db.query(Product).filter(Product.id == consumption.product_id).first()
            if product:
                # 恢复库存
                product.stock = product.stock + consumption.quantity
        
        # 3. 删除所有关联记录
        # 删除房间客户关联
        db.query(RoomCustomer).filter(RoomCustomer.session_id == session_id).delete()
        
        # 删除借款记录
        db.query(CustomerLoan).filter(CustomerLoan.session_id == session_id).delete()
        
        # 删除还款记录
        db.query(CustomerRepayment).filter(CustomerRepayment.session_id == session_id).delete()
        
        # 删除商品消费记录
        db.query(ProductConsumption).filter(ProductConsumption.session_id == session_id).delete()
        
        # 删除餐费记录
        db.query(MealRecord).filter(MealRecord.session_id == session_id).delete()
        
        # 删除房间转移记录
        db.query(RoomTransfer).filter(RoomTransfer.session_id == session_id).delete()
        
        # 4. 软删除房间使用记录（设置 deleted_at，保留数据以便恢复）
        session.deleted_at = datetime.now(timezone.utc)
        
        # 5. 更新房间状态为idle（如果删除的是最后一次记录）
        # 检查是否还有其他进行中的记录（不包括已删除的）
        active_session = db.query(RoomSession).filter(
            RoomSession.room_id == room_id,
            RoomSession.status == "in_progress",
            RoomSession.deleted_at.is_(None)
        ).first()
        
        if not active_session:
            room.status = "idle"
        
        db.commit()
        
        return {
            "message": f"已删除房间 {room.name} 的使用记录（ID: {session_id}），可以恢复",
            "deleted_session_id": session_id,
            "room_id": room_id,
            "room_name": room.name,
            "deleted_at": session.deleted_at.isoformat()
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/sessions/{session_id}/restore")
def restore_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    恢复已删除的房间使用记录
    
    功能说明：
    - 恢复已删除的房间使用记录（清除 deleted_at）
    - 恢复所有相关的财务数据（客户余额、库存等）
    - 恢复所有关联记录（客户关联、借款、还款、商品消费、餐费记录、房间转移记录）
    """
    # 查找已删除的房间使用记录
    session = db.query(RoomSession).filter(
        RoomSession.id == session_id,
        RoomSession.deleted_at.isnot(None)
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="房间使用记录不存在或未被删除")
    
    room_id = session.room_id
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    try:
        # 1. 恢复客户余额（处理借款和还款）
        # 获取所有借款记录
        loans = db.query(CustomerLoan).filter(
            CustomerLoan.session_id == session_id
        ).all()
        for loan in loans:
            customer = db.query(Customer).filter(Customer.id == loan.customer_id).first()
            if customer:
                # 恢复借款对客户余额的影响（减少balance，增加欠款）
                customer.balance = customer.balance - loan.amount
        
        # 获取所有还款记录
        repayments = db.query(CustomerRepayment).filter(
            CustomerRepayment.session_id == session_id
        ).all()
        for repayment in repayments:
            customer = db.query(Customer).filter(Customer.id == repayment.customer_id).first()
            if customer:
                # 恢复还款对客户余额的影响（增加balance，减少欠款）
                customer.balance = customer.balance + repayment.amount
                
                # 如果有关联的借款记录，需要更新借款状态
                if repayment.loan_id:
                    loan = db.query(CustomerLoan).filter(CustomerLoan.id == repayment.loan_id).first()
                    if loan:
                        # 更新借款的剩余金额
                        loan.remaining_amount = loan.remaining_amount - repayment.amount
                        # 如果还款金额大于等于借款金额，借款状态更新为repaid
                        if loan.remaining_amount <= 0:
                            loan.status = "repaid"
        
        # 2. 恢复商品库存（减少库存）
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session_id
        ).all()
        for consumption in consumptions:
            product = db.query(Product).filter(Product.id == consumption.product_id).first()
            if product:
                # 减少库存
                product.stock = product.stock - consumption.quantity
        
        # 3. 恢复房间使用记录（清除 deleted_at）
        session.deleted_at = None
        
        # 4. 更新房间状态（如果房间当前是idle，且恢复的记录是进行中，则更新为in_use）
        if session.status == "in_progress":
            room.status = "in_use"
        
        db.commit()
        
        return {
            "message": f"已恢复房间 {room.name} 的使用记录（ID: {session_id}）",
            "restored_session_id": session_id,
            "room_id": room_id,
            "room_name": room.name
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")


@router.delete("/{room_id}/last-session")
def delete_last_session(
    room_id: int,
    db: Session = Depends(get_db)
):
    """
    删除指定房间的最后一次已结算使用记录
    
    功能说明：
    - 找到指定房间的最后一次已结算记录（按结束时间倒序，取第一条）
    - 回滚所有相关的财务数据（客户余额、库存等）
    - 删除所有关联记录（客户关联、借款、还款、商品消费、餐费记录、房间转移记录）
    - 删除房间使用记录本身
    - 更新房间状态为idle（如果删除的是最后一次记录）
    """
    # 检查房间是否存在
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 查找最后一次已结算的记录（按结束时间倒序，取第一条）
    session = db.query(RoomSession).filter(
        RoomSession.room_id == room_id,
        RoomSession.status == "settled"
    ).order_by(RoomSession.end_time.desc()).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="该房间没有已结算的使用记录")
    
    session_id = session.id
    
    try:
        # 1. 回滚客户余额（处理借款和还款）
        # 获取所有借款记录
        loans = db.query(CustomerLoan).filter(
            CustomerLoan.session_id == session_id
        ).all()
        for loan in loans:
            customer = db.query(Customer).filter(Customer.id == loan.customer_id).first()
            if customer:
                # 借款时减少了balance（增加欠款），删除时需要增加balance（减少欠款）
                customer.balance = customer.balance + loan.amount
                # 恢复借款记录状态
                loan.status = "active"
                loan.remaining_amount = loan.amount
        
        # 获取所有还款记录
        repayments = db.query(CustomerRepayment).filter(
            CustomerRepayment.session_id == session_id
        ).all()
        for repayment in repayments:
            customer = db.query(Customer).filter(Customer.id == repayment.customer_id).first()
            if customer:
                # 还款时增加了balance（减少欠款），删除时需要减少balance（增加欠款）
                customer.balance = customer.balance - repayment.amount
                
                # 如果有关联的借款记录，需要恢复借款状态
                if repayment.loan_id:
                    loan = db.query(CustomerLoan).filter(CustomerLoan.id == repayment.loan_id).first()
                    if loan:
                        # 恢复借款的剩余金额
                        loan.remaining_amount = loan.remaining_amount + repayment.amount
                        # 如果还款金额大于等于借款金额，借款状态恢复为active
                        if loan.remaining_amount > 0:
                            loan.status = "active"
        
        # 2. 恢复商品库存
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session_id
        ).all()
        for consumption in consumptions:
            product = db.query(Product).filter(Product.id == consumption.product_id).first()
            if product:
                # 恢复库存
                product.stock = product.stock + consumption.quantity
        
        # 3. 删除所有关联记录
        # 删除房间客户关联
        db.query(RoomCustomer).filter(RoomCustomer.session_id == session_id).delete()
        
        # 删除借款记录
        db.query(CustomerLoan).filter(CustomerLoan.session_id == session_id).delete()
        
        # 删除还款记录
        db.query(CustomerRepayment).filter(CustomerRepayment.session_id == session_id).delete()
        
        # 删除商品消费记录
        db.query(ProductConsumption).filter(ProductConsumption.session_id == session_id).delete()
        
        # 删除餐费记录
        db.query(MealRecord).filter(MealRecord.session_id == session_id).delete()
        
        # 删除房间转移记录
        db.query(RoomTransfer).filter(RoomTransfer.session_id == session_id).delete()
        
        # 4. 删除房间使用记录本身
        db.delete(session)
        
        # 5. 更新房间状态为idle（如果删除的是最后一次记录）
        # 检查是否还有其他进行中的记录
        active_session = db.query(RoomSession).filter(
            RoomSession.room_id == room_id,
            RoomSession.status == "in_progress"
        ).first()
        
        if not active_session:
            room.status = "idle"
        
        db.commit()
        
        return {
            "message": f"已删除房间 {room.name} 的最后一次使用记录（ID: {session_id}）",
            "deleted_session_id": session_id,
            "room_id": room_id,
            "room_name": room.name
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{room_id}/reset")
def reset_room(
    room_id: int,
    db: Session = Depends(get_db)
):
    """
    重置房间到开始使用前的状态
    
    功能说明：
    - 找到指定房间的进行中使用记录（status = in_progress）
    - 回滚所有相关的财务数据（客户余额、库存等）
    - 删除所有关联记录（客户关联、借款、还款、商品消费、餐费记录、房间转移记录）
    - 删除房间使用记录本身
    - 将房间状态改为idle
    """
    # 检查房间是否存在
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 查找进行中的使用记录
    session = db.query(RoomSession).filter(
        RoomSession.room_id == room_id,
        RoomSession.status == "in_progress"
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="该房间没有进行中的使用记录")
    
    session_id = session.id
    
    try:
        # 1. 回滚客户余额（处理借款和还款）
        # 获取所有借款记录
        loans = db.query(CustomerLoan).filter(
            CustomerLoan.session_id == session_id
        ).all()
        for loan in loans:
            customer = db.query(Customer).filter(Customer.id == loan.customer_id).first()
            if customer:
                # 借款时减少了balance（增加欠款），删除时需要增加balance（减少欠款）
                customer.balance = customer.balance + loan.amount
        
        # 获取所有还款记录
        repayments = db.query(CustomerRepayment).filter(
            CustomerRepayment.session_id == session_id
        ).all()
        for repayment in repayments:
            customer = db.query(Customer).filter(Customer.id == repayment.customer_id).first()
            if customer:
                # 还款时增加了balance（减少欠款），删除时需要减少balance（增加欠款）
                customer.balance = customer.balance - repayment.amount
                
                # 如果有关联的借款记录，需要恢复借款状态
                if repayment.loan_id:
                    loan = db.query(CustomerLoan).filter(CustomerLoan.id == repayment.loan_id).first()
                    if loan:
                        # 恢复借款的剩余金额
                        loan.remaining_amount = loan.remaining_amount + repayment.amount
                        # 如果还款金额大于等于借款金额，借款状态恢复为active
                        if loan.remaining_amount > 0:
                            loan.status = "active"
        
        # 2. 恢复商品库存
        consumptions = db.query(ProductConsumption).filter(
            ProductConsumption.session_id == session_id
        ).all()
        for consumption in consumptions:
            product = db.query(Product).filter(Product.id == consumption.product_id).first()
            if product:
                # 恢复库存
                product.stock = product.stock + consumption.quantity
        
        # 3. 删除所有关联记录
        # 删除房间客户关联
        db.query(RoomCustomer).filter(RoomCustomer.session_id == session_id).delete()
        
        # 删除借款记录
        db.query(CustomerLoan).filter(CustomerLoan.session_id == session_id).delete()
        
        # 删除还款记录
        db.query(CustomerRepayment).filter(CustomerRepayment.session_id == session_id).delete()
        
        # 删除商品消费记录
        db.query(ProductConsumption).filter(ProductConsumption.session_id == session_id).delete()
        
        # 删除餐费记录
        db.query(MealRecord).filter(MealRecord.session_id == session_id).delete()
        
        # 删除房间转移记录
        db.query(RoomTransfer).filter(RoomTransfer.session_id == session_id).delete()
        
        # 4. 删除房间使用记录本身
        db.delete(session)
        
        # 5. 将房间状态改为idle
        room.status = "idle"
        
        db.commit()
        
        return {
            "message": f"已将房间 {room.name} 恢复到开始使用前的状态",
            "room_id": room_id,
            "room_name": room.name,
            "deleted_session_id": session_id
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")

