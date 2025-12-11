"""
客户管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timezone
from app.db.database import get_db
from app.models.customer import Customer
from app.models.customer_loan import CustomerLoan
from app.models.customer_repayment import CustomerRepayment
from app.models.transfer import Transfer
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse, CustomerTransfer, CustomerBatchDelete
)
from app.schemas.loan import LoanResponse, RepaymentResponse, RepaymentCreate
from decimal import Decimal

router = APIRouter(prefix="/api/customers", tags=["客户管理"])


@router.get("", response_model=List[CustomerResponse])
def get_customers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """获取客户列表"""
    query = db.query(Customer)
    
    # 默认不显示已删除的客户
    if not include_deleted:
        query = query.filter(or_(Customer.is_deleted == 0, Customer.is_deleted == None))
    
    if search:
        query = query.filter(
            or_(
                Customer.name.like(f"%{search}%"),
                Customer.phone.like(f"%{search}%")
            )
        )
    
    customers = query.offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """获取客户详情"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


@router.post("", response_model=CustomerResponse)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """创建客户"""
    # 检查客户姓名是否已存在（排除已删除的客户）
    existing_customer = db.query(Customer).filter(
        Customer.name == customer.name,
        or_(Customer.is_deleted == 0, Customer.is_deleted == None)
    ).first()
    
    if existing_customer:
        raise HTTPException(status_code=400, detail=f"客户姓名 '{customer.name}' 已存在，请使用其他姓名")
    
    # 处理初期帐单逻辑
    initial_balance = customer.initial_balance or Decimal(0)
    
    # balance字段：负数=欠款，正数=预存（存款）
    # 直接使用initial_balance作为balance的初始值
    balance = initial_balance
    # deposit字段保持兼容（如果balance为正数，deposit也设为相同值）
    deposit = initial_balance if initial_balance > 0 else Decimal(0)
    
    db_customer = Customer(
        name=customer.name,
        phone=customer.phone,
        initial_balance=initial_balance,
        balance=balance,
        deposit=deposit
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db)
):
    """更新客户"""
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    update_data = customer_update.dict(exclude_unset=True)
    
    # 如果更新了客户姓名，检查新姓名是否已存在（排除当前客户和已删除的客户）
    if "name" in update_data and update_data["name"] != db_customer.name:
        existing_customer = db.query(Customer).filter(
            Customer.name == update_data["name"],
            Customer.id != customer_id,
            or_(Customer.is_deleted == 0, Customer.is_deleted == None)
        ).first()
        
        if existing_customer:
            raise HTTPException(status_code=400, detail=f"客户姓名 '{update_data['name']}' 已存在，请使用其他姓名")
    
    for field, value in update_data.items():
        setattr(db_customer, field, value)
    
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get("/{customer_id}/loans", response_model=List[LoanResponse])
def get_customer_loans(customer_id: int, db: Session = Depends(get_db)):
    """获取客户借款记录"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    loans = db.query(CustomerLoan).filter(
        CustomerLoan.customer_id == customer_id
    ).order_by(CustomerLoan.created_at.desc()).all()
    return loans


@router.put("/{customer_id}/loans/{loan_id}/description")
def update_loan_description(
    customer_id: int,
    loan_id: int,
    description: str = Query(..., description="说明内容"),
    db: Session = Depends(get_db)
):
    """更新借款记录说明"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    loan = db.query(CustomerLoan).filter(
        CustomerLoan.id == loan_id,
        CustomerLoan.customer_id == customer_id
    ).first()
    if not loan:
        raise HTTPException(status_code=404, detail="借款记录不存在")
    
    loan.description = description
    db.commit()
    return {"message": "说明已更新", "description": description}


@router.put("/{customer_id}/repayments/{repayment_id}/description")
def update_repayment_description(
    customer_id: int,
    repayment_id: int,
    description: str = Query(..., description="说明内容"),
    db: Session = Depends(get_db)
):
    """更新还款记录说明"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    repayment = db.query(CustomerRepayment).filter(
        CustomerRepayment.id == repayment_id,
        CustomerRepayment.customer_id == customer_id
    ).first()
    if not repayment:
        raise HTTPException(status_code=404, detail="还款记录不存在")
    
    repayment.description = description
    db.commit()
    return {"message": "说明已更新", "description": description}


@router.delete("/{customer_id}/loans/{loan_id}")
def delete_loan(
    customer_id: int,
    loan_id: int,
    session_id: Optional[int] = Query(None, description="房间会话ID，用于验证是否是最后一条记录"),
    db: Session = Depends(get_db)
):
    """删除借款记录（只能删除最后一条）"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    loan = db.query(CustomerLoan).filter(
        CustomerLoan.id == loan_id,
        CustomerLoan.customer_id == customer_id
    ).first()
    if not loan:
        raise HTTPException(status_code=404, detail="借款记录不存在")
    
    # 如果提供了session_id，只检查该会话中的记录
    if session_id:
        # 检查是否是该会话中最后一条记录（借款或还款，按创建时间排序）
        all_loans = db.query(CustomerLoan).filter(
            CustomerLoan.session_id == session_id,
            CustomerLoan.customer_id == customer_id
        ).order_by(CustomerLoan.created_at.desc()).all()
        
        all_repayments = db.query(CustomerRepayment).filter(
            CustomerRepayment.session_id == session_id,
            CustomerRepayment.customer_id == customer_id
        ).order_by(CustomerRepayment.created_at.desc()).all()
        
        # 合并所有记录，按创建时间排序
        all_records = []
        for l in all_loans:
            all_records.append(('loan', l.id, l.created_at))
        for r in all_repayments:
            all_records.append(('repayment', r.id, r.created_at))
        
        all_records.sort(key=lambda x: x[2], reverse=True)
        
        if not all_records or all_records[0][0] != 'loan' or all_records[0][1] != loan_id:
            raise HTTPException(status_code=400, detail="只能删除最后一条记录")
    else:
        # 检查是否是最后一条借款记录（按创建时间排序）
        all_loans = db.query(CustomerLoan).filter(
            CustomerLoan.customer_id == customer_id
        ).order_by(CustomerLoan.created_at.desc()).all()
        
        if not all_loans or all_loans[0].id != loan_id:
            raise HTTPException(status_code=400, detail="只能删除最后一条借款记录")
    
    # 回滚客户余额：借款时减少了balance，删除时需要增加balance
    customer.balance = customer.balance + loan.amount
    
    # 如果借款已被还款，需要恢复还款记录关联的借款状态
    repayments = db.query(CustomerRepayment).filter(
        CustomerRepayment.loan_id == loan_id
    ).all()
    
    for repayment in repayments:
        # 回滚还款对客户余额的影响
        customer.balance = customer.balance - repayment.amount
        # 恢复借款的剩余金额
        loan.remaining_amount = loan.remaining_amount + repayment.amount
        if loan.remaining_amount > 0:
            loan.status = "active"
    
    # 删除借款记录
    db.delete(loan)
    db.commit()
    
    return {"message": "借款记录已删除"}


@router.delete("/{customer_id}/repayments/{repayment_id}")
def delete_repayment(
    customer_id: int,
    repayment_id: int,
    session_id: Optional[int] = Query(None, description="房间会话ID，用于验证是否是最后一条记录"),
    db: Session = Depends(get_db)
):
    """删除还款记录（只能删除最后一条）"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    repayment = db.query(CustomerRepayment).filter(
        CustomerRepayment.id == repayment_id,
        CustomerRepayment.customer_id == customer_id
    ).first()
    if not repayment:
        raise HTTPException(status_code=404, detail="还款记录不存在")
    
    # 如果提供了session_id，只检查该会话中的记录
    if session_id:
        # 检查是否是该会话中最后一条记录（借款或还款，按创建时间排序）
        all_loans = db.query(CustomerLoan).filter(
            CustomerLoan.session_id == session_id,
            CustomerLoan.customer_id == customer_id
        ).order_by(CustomerLoan.created_at.desc()).all()
        
        all_repayments = db.query(CustomerRepayment).filter(
            CustomerRepayment.session_id == session_id,
            CustomerRepayment.customer_id == customer_id
        ).order_by(CustomerRepayment.created_at.desc()).all()
        
        # 合并所有记录，按创建时间排序
        all_records = []
        for l in all_loans:
            all_records.append(('loan', l.id, l.created_at))
        for r in all_repayments:
            all_records.append(('repayment', r.id, r.created_at))
        
        all_records.sort(key=lambda x: x[2], reverse=True)
        
        if not all_records or all_records[0][0] != 'repayment' or all_records[0][1] != repayment_id:
            raise HTTPException(status_code=400, detail="只能删除最后一条记录")
    else:
        # 检查是否是最后一条还款记录（按创建时间排序）
        all_repayments = db.query(CustomerRepayment).filter(
            CustomerRepayment.customer_id == customer_id
        ).order_by(CustomerRepayment.created_at.desc()).all()
        
        if not all_repayments or all_repayments[0].id != repayment_id:
            raise HTTPException(status_code=400, detail="只能删除最后一条还款记录")
    
    # 回滚客户余额：还款时增加了balance，删除时需要减少balance
    customer.balance = customer.balance - repayment.amount
    
    # 如果还款关联了借款记录，需要恢复借款状态
    if repayment.loan_id:
        loan = db.query(CustomerLoan).filter(CustomerLoan.id == repayment.loan_id).first()
        if loan:
            # 恢复借款的剩余金额
            loan.remaining_amount = loan.remaining_amount + repayment.amount
            # 如果还款金额大于等于借款金额，借款状态恢复为active
            if loan.remaining_amount > 0:
                loan.status = "active"
    
    # 删除还款记录
    db.delete(repayment)
    db.commit()
    
    return {"message": "还款记录已删除"}


@router.get("/{customer_id}/repayments", response_model=List[RepaymentResponse])
def get_customer_repayments(customer_id: int, db: Session = Depends(get_db)):
    """获取客户还款记录"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    repayments = db.query(CustomerRepayment).filter(
        CustomerRepayment.customer_id == customer_id
    ).order_by(CustomerRepayment.created_at.desc()).all()
    return repayments


@router.post("/{customer_id}/repayment")
def create_customer_repayment(
    customer_id: int,
    repayment: RepaymentCreate,
    db: Session = Depends(get_db)
):
    """客户还款（从客户列表直接还款）"""
    # 验证客户是否存在
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 确保customer_id匹配
    if repayment.customer_id != customer_id:
        raise HTTPException(status_code=400, detail="客户ID不匹配")
    
    repay_amount = Decimal(str(repayment.amount))
    is_refund = repay_amount < 0  # 负数表示退款/支付给客户
    abs_amount = abs(repay_amount)
    
    loan_repay = Decimal('0')
    extra_repay = Decimal('0')
    
    if is_refund:
        # 负数：退款/支付给客户（减少balance，可能增加欠款或减少预存）
        # 直接更新balance，不需要处理借款记录
        customer.balance = customer.balance + repay_amount  # repay_amount是负数，所以是减少
        
        # 如果余额为正，更新deposit
        if customer.balance > 0:
            customer.deposit = customer.balance
        else:
            customer.deposit = Decimal('0')
        
        message = f"退款成功，已向客户支付 ¥{abs_amount:.2f}"
    else:
        # 正数：正常还款（增加balance，减少欠款或增加预存）
        # 如果有借款记录，优先还借款
        if repayment.loan_id:
            # 获取指定的借款记录
            loan = db.query(CustomerLoan).filter(CustomerLoan.id == repayment.loan_id).first()
            if not loan:
                raise HTTPException(status_code=404, detail="借款记录不存在")
            
            if loan.customer_id != customer_id:
                raise HTTPException(status_code=400, detail="借款记录与客户不匹配")
            
            remaining_amount = Decimal(str(loan.remaining_amount))
            
            # 计算还款金额中用于还此笔借款的部分和超出的部分
            if repay_amount <= remaining_amount:
                loan_repay = repay_amount
                extra_repay = Decimal('0')
            else:
                loan_repay = remaining_amount
                extra_repay = repay_amount - remaining_amount
            
            # 更新借款状态
            loan.remaining_amount = max(Decimal('0'), loan.remaining_amount - loan_repay)
            if loan.remaining_amount <= 0:
                loan.status = "repaid"
        else:
            # 没有指定借款记录，查找是否有未还清的借款
            active_loan = db.query(CustomerLoan).filter(
                CustomerLoan.customer_id == customer_id,
                CustomerLoan.status == "active",
                CustomerLoan.remaining_amount > 0
            ).order_by(CustomerLoan.created_at.asc()).first()
            
            if active_loan:
                remaining_amount = Decimal(str(active_loan.remaining_amount))
                
                if repay_amount <= remaining_amount:
                    loan_repay = repay_amount
                    extra_repay = Decimal('0')
                else:
                    loan_repay = remaining_amount
                    extra_repay = repay_amount - remaining_amount
                
                # 更新借款状态
                active_loan.remaining_amount = max(Decimal('0'), active_loan.remaining_amount - loan_repay)
                if active_loan.remaining_amount <= 0:
                    active_loan.status = "repaid"
                
                repayment.loan_id = active_loan.id
            else:
                loan_repay = Decimal('0')
                extra_repay = repay_amount
        
        # 更新客户总帐：还款增加balance（减少欠款或增加预存）
        # balance负数=欠款，正数=预存，还款应该增加balance
        customer.balance = customer.balance + repay_amount
        
        # 如果余额为正，更新deposit
        if customer.balance > 0:
            customer.deposit = customer.balance
        else:
            customer.deposit = Decimal('0')
        
        # 生成消息
        if loan_repay > 0 and extra_repay > 0:
            message = f"还款成功，其中 ¥{loan_repay:.2f} 用于还清借款，¥{extra_repay:.2f} 已冲抵总欠款"
        elif loan_repay > 0:
            message = f"还款成功，¥{loan_repay:.2f} 用于还清借款"
        elif extra_repay > 0:
            message = f"还款成功，¥{extra_repay:.2f} 已冲抵总欠款"
        else:
            message = "还款成功"
    
    # 生成说明（在创建记录之前）
    payment_method = repayment.payment_method or "现金"
    if is_refund:
        description = f"退款/支付给客户 ({payment_method})"
    else:
        # 确定loan_id
        loan_id = None
        if repayment.loan_id:
            loan_id = repayment.loan_id
        elif loan_repay > 0:
            # 查找active_loan（在else分支中定义）
            if 'active_loan' in locals() and active_loan:
                loan_id = active_loan.id
            # 如果repayment.loan_id在else分支中被设置
            if not loan_id and hasattr(repayment, 'loan_id') and repayment.loan_id:
                loan_id = repayment.loan_id
        
        if loan_id:
            description = f"还款 - 关联借款ID: {loan_id} ({payment_method})"
        else:
            description = f"还款 - 还总欠款 ({payment_method})"
    
    # 创建还款记录（金额可以是负数）
    db_repayment = CustomerRepayment(
        customer_id=customer_id,
        loan_id=repayment.loan_id,
        amount=repay_amount,  # 可以是负数
        payment_method=payment_method,
        description=description,
        session_id=repayment.session_id
    )
    db.add(db_repayment)
    
    db.commit()
    db.refresh(customer)
    db.refresh(db_repayment)
    
    result = {
        "message": message,
        "repayment_id": db_repayment.id,
        "customer_balance": float(customer.balance),
        "loan_repay": float(loan_repay),
        "extra_repay": float(extra_repay)
    }
    
    return result


@router.post("/transfer")
def transfer_customer_debt(transfer: CustomerTransfer, db: Session = Depends(get_db)):
    """客户转账（转移款）"""
    # 检查转出方
    from_customer = db.query(Customer).filter(Customer.id == transfer.from_customer_id).first()
    if not from_customer:
        raise HTTPException(status_code=404, detail="转出方客户不存在")
    
    # 检查转入方
    to_customer = db.query(Customer).filter(Customer.id == transfer.to_customer_id).first()
    if not to_customer:
        raise HTTPException(status_code=404, detail="转入方客户不存在")
    
    # 不能自己转给自己
    if transfer.from_customer_id == transfer.to_customer_id:
        raise HTTPException(status_code=400, detail="不能自己转给自己")
    
    # 检查转出方是否有足够欠款
    # balance负数=欠款，正数=预存，转账需要转出方有欠款（balance < 0）且欠款金额足够
    if from_customer.balance >= 0 or abs(from_customer.balance) < transfer.amount:
        raise HTTPException(status_code=400, detail="转出方欠款余额不足")
    
    # 查找转出方的未还清借款记录（按时间排序，优先转移最早的）
    original_loan = db.query(CustomerLoan).filter(
        CustomerLoan.customer_id == transfer.from_customer_id,
        CustomerLoan.status == "active",
        CustomerLoan.remaining_amount > 0
    ).order_by(CustomerLoan.created_at.asc()).first()
    
    if not original_loan:
        raise HTTPException(status_code=400, detail="转出方没有可转移的借款记录")
    
    if original_loan.remaining_amount < transfer.amount:
        raise HTTPException(status_code=400, detail="转出方该笔借款剩余金额不足")
    
    # 开始事务处理
    try:
        # 1. 创建transfer记录
        from app.models.transfer import Transfer
        transfer_record = Transfer(
            from_customer_id=transfer.from_customer_id,
            to_customer_id=transfer.to_customer_id,
            amount=transfer.amount,
            original_loan_id=original_loan.id
        )
        db.add(transfer_record)
        db.flush()  # 获取transfer_record.id
        
        # 2. 更新转出方的借款记录
        original_loan.status = "transferred"
        original_loan.remaining_amount = original_loan.remaining_amount - transfer.amount
        
        # 3. 创建转入方的新借款记录
        from app.models.customer_loan import CustomerLoan
        # 生成说明
        new_description = f"向麻将馆借款 - 剩余未还: ¥{transfer.amount:.2f} - 正常"
        new_loan = CustomerLoan(
            customer_id=transfer.to_customer_id,
            amount=transfer.amount,
            loan_type="from_shop",
            status="active",
            remaining_amount=transfer.amount,
            description=new_description,
            transfer_from_id=transfer_record.id
        )
        db.add(new_loan)
        db.flush()  # 获取new_loan.id
        
        # 4. 更新transfer记录的new_loan_id
        transfer_record.new_loan_id = new_loan.id
        
        # 5. 更新客户余额
        from_customer.balance = from_customer.balance - transfer.amount
        to_customer.balance = to_customer.balance + transfer.amount
        
        db.commit()
        
        return {
            "message": "转账成功",
            "transfer_id": transfer_record.id,
            "from_customer_balance": float(from_customer.balance),
            "to_customer_balance": float(to_customer.balance)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"转账失败: {str(e)}")


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """删除单个客户（软删除）"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 检查是否已被删除
    if customer.is_deleted == 1:
        raise HTTPException(status_code=400, detail="该客户已被删除")
    
    # 检查是否有未结清的欠款或存款
    # balance负数=欠款，正数=预存
    if customer.balance < 0:
        raise HTTPException(status_code=400, detail=f"该客户还有未结清的欠款 ¥{abs(customer.balance)}，无法删除")
    if customer.balance > 0:
        raise HTTPException(status_code=400, detail=f"该客户还有预存余额 ¥{customer.balance}，无法删除")
    
    try:
        # 软删除：标记为已删除
        customer.is_deleted = 1
        customer.deleted_at = datetime.now(timezone.utc)
        db.commit()
        return {"message": "删除成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/batch-delete")
def batch_delete_customers(data: CustomerBatchDelete, db: Session = Depends(get_db)):
    """批量删除客户（软删除）"""
    if not data.ids:
        raise HTTPException(status_code=400, detail="请选择要删除的客户")
    
    # 检查所有客户是否存在且未被删除
    customers = db.query(Customer).filter(
        Customer.id.in_(data.ids),
        or_(Customer.is_deleted == 0, Customer.is_deleted == None)
    ).all()
    
    if len(customers) != len(data.ids):
        raise HTTPException(status_code=404, detail="部分客户不存在或已被删除")
    
    # 检查是否有未结清的欠款或存款，收集所有不能删除的客户
    # balance负数=欠款，正数=预存
    cannot_delete = []
    can_delete = []
    for customer in customers:
        if customer.balance < 0:
            cannot_delete.append(f"{customer.name}(欠款¥{abs(customer.balance)})")
        elif customer.balance > 0:
            cannot_delete.append(f"{customer.name}(预存¥{customer.balance})")
        else:
            can_delete.append(customer)
    
    if cannot_delete:
        raise HTTPException(
            status_code=400, 
            detail=f"以下客户有未结清款项，无法删除：{', '.join(cannot_delete)}"
        )
    
    try:
        # 软删除：标记为已删除
        now = datetime.now(timezone.utc)
        for customer in can_delete:
            customer.is_deleted = 1
            customer.deleted_at = now
        db.commit()
        return {"message": f"成功删除 {len(can_delete)} 个客户"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")




