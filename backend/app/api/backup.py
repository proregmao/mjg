"""
数据备份、还原和清理API
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.db.database import get_db, DATABASE_URL
from app.models.customer import Customer
from app.models.customer_loan import CustomerLoan
from app.models.customer_repayment import CustomerRepayment
from app.models.room import Room
from app.models.room_session import RoomSession
from app.models.room_customer import RoomCustomer
from app.models.product import Product
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord
from app.models.transfer import Transfer
from app.models.room_transfer import RoomTransfer
from app.models.supplier import Supplier
from app.models.purchase import Purchase, PurchaseItem
from app.models.other_expense import OtherExpense
from app.models.other_income import OtherIncome
from app.models.system_config import SystemConfig
from app.models.operation_log import OperationLog
from app.models.user import User
from typing import Optional, List
import os
import shutil
from datetime import datetime
from pathlib import Path
import sqlite3

router = APIRouter(prefix="/api/backup", tags=["backup"])

# 备份目录
BACKUP_DIR = Path(__file__).parent.parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


class RestoreRequest(BaseModel):
    filename: str


class DeleteRequest(BaseModel):
    filename: str


class CleanDataRequest(BaseModel):
    """数据清理请求模型"""
    clean_customers: bool = Field(False, description="清理客户数据")
    clean_products: bool = Field(False, description="清理商品数据")
    clean_rooms: bool = Field(False, description="清理房间数据")
    clean_sessions: bool = Field(False, description="清理房间会话数据")
    clean_loans_repayments: bool = Field(False, description="清理借款还款数据")
    clean_transfers: bool = Field(False, description="清理转账数据")
    clean_suppliers: bool = Field(False, description="清理供应商数据")
    clean_purchases: bool = Field(False, description="清理进货数据")
    clean_other_income: bool = Field(False, description="清理其它收入数据")
    clean_other_expense: bool = Field(False, description="清理其它支出数据")
    clean_system_config: bool = Field(False, description="清理系统配置（包括初期现金）")
    clean_operation_logs: bool = Field(False, description="清理操作日志")
    clean_users: bool = Field(False, description="清理用户数据（默认不清理）")


def get_database_path():
    """获取数据库文件路径"""
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            # 相对路径，从backend目录开始
            db_path = Path(__file__).parent.parent.parent / db_path
        return Path(db_path)
    raise HTTPException(status_code=500, detail="不支持的数据库类型")


@router.post("/create")
def create_backup():
    """创建数据备份"""
    try:
        db_path = get_database_path()
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="数据库文件不存在")
        
        # 生成备份文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = BACKUP_DIR / backup_filename
        
        # 复制数据库文件
        shutil.copy2(db_path, backup_path)
        
        # 获取备份文件大小
        backup_size = backup_path.stat().st_size
        
        return {
            "message": "备份成功",
            "filename": backup_filename,
            "path": str(backup_path),
            "size": backup_size,
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {str(e)}")


@router.get("/list")
def list_backups():
    """获取备份列表"""
    try:
        backups = []
        # 获取所有.db文件（包括backup_、clean_backup_、upload_backup_等）
        for file in sorted(BACKUP_DIR.glob("*.db"), reverse=True):
            stat = file.stat()
            backups.append({
                "filename": file.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(file)
            })
        return {"backups": backups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")


@router.post("/restore")
def restore_backup(request: RestoreRequest):
    """还原备份"""
    try:
        backup_path = BACKUP_DIR / request.filename
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="备份文件不存在")
        
        db_path = get_database_path()
        
        # 还原前先创建备份
        restore_backup_filename = f"restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        restore_backup_path = BACKUP_DIR / restore_backup_filename
        if db_path.exists():
            shutil.copy2(db_path, restore_backup_path)
        
        # 复制备份文件到数据库位置
        shutil.copy2(backup_path, db_path)
        
        return {
            "message": "还原成功",
            "restored_file": request.filename,
            "restore_backup": restore_backup_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"还原失败: {str(e)}")


@router.delete("/delete")
def delete_backup(request: DeleteRequest):
    """删除备份文件"""
    try:
        backup_path = BACKUP_DIR / request.filename
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="备份文件不存在")
        
        backup_path.unlink()
        
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/clean")
def clean_data(request: CleanDataRequest, db: Session = Depends(get_db)):
    """清理数据（清理前自动备份，支持选择性清理）"""
    # 只清理用户明确选择的数据（默认值都是False，不会清理未选择的数据）
    
    backup_filename = None
    cleaned_items = []
    
    try:
        # 1. 清理前自动备份
        db_path = get_database_path()
        if db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"clean_backup_{timestamp}.db"
            backup_path = BACKUP_DIR / backup_filename
            shutil.copy2(db_path, backup_path)
        
        # 2. 按照外键依赖关系的逆序删除
        # 注意：需要按照外键依赖关系的逆序删除
        
        # 删除还款记录（如果清理借款还款数据）
        if request.clean_loans_repayments:
            count = db.query(CustomerRepayment).delete()
            if count > 0:
                cleaned_items.append(f"还款记录({count}条)")
        
        # 删除借款记录（如果清理借款还款数据）
        if request.clean_loans_repayments:
            count = db.query(CustomerLoan).delete()
            if count > 0:
                cleaned_items.append(f"借款记录({count}条)")
        
        # 删除转账记录（如果清理转账数据）
        if request.clean_transfers:
            count1 = db.query(RoomTransfer).delete()
            count2 = db.query(Transfer).delete()
            if count1 + count2 > 0:
                cleaned_items.append(f"转账记录({count1 + count2}条)")
        
        # 删除房间客户关联（如果清理会话数据）
        if request.clean_sessions:
            count = db.query(RoomCustomer).delete()
            if count > 0:
                cleaned_items.append(f"房间客户关联({count}条)")
        
        # 删除房间会话（如果清理会话数据）
        if request.clean_sessions:
            count = db.query(RoomSession).delete()
            if count > 0:
                cleaned_items.append(f"房间会话({count}条)")
        
        # 删除商品消费记录（如果清理会话数据）
        if request.clean_sessions:
            count = db.query(ProductConsumption).delete()
            if count > 0:
                cleaned_items.append(f"商品消费记录({count}条)")
        
        # 删除餐费记录（如果清理会话数据）
        if request.clean_sessions:
            count = db.query(MealRecord).delete()
            if count > 0:
                cleaned_items.append(f"餐费记录({count}条)")
        
        # 删除进货相关数据（如果清理进货数据，必须先删除进货项，再删除进货单）
        if request.clean_purchases:
            count1 = db.query(PurchaseItem).delete()
            count2 = db.query(Purchase).delete()
            if count1 + count2 > 0:
                cleaned_items.append(f"进货数据({count1 + count2}条)")
        
        # 删除供应商（如果清理供应商数据）
        if request.clean_suppliers:
            count = db.query(Supplier).delete()
            if count > 0:
                cleaned_items.append(f"供应商({count}条)")
        
        # 删除客户（如果清理客户数据，软删除的也要清理）
        if request.clean_customers:
            count = db.query(Customer).delete()
            if count > 0:
                cleaned_items.append(f"客户({count}条)")
        
        # 删除房间（如果清理房间数据）
        if request.clean_rooms:
            count = db.query(Room).delete()
            if count > 0:
                cleaned_items.append(f"房间({count}条)")
        
        # 删除商品（如果清理商品数据）
        if request.clean_products:
            count = db.query(Product).delete()
            if count > 0:
                cleaned_items.append(f"商品({count}条)")
        
        # 删除其它收入（如果清理其它收入数据）
        if request.clean_other_income:
            count = db.query(OtherIncome).delete()
            if count > 0:
                cleaned_items.append(f"其它收入({count}条)")
        
        # 删除其它支出（如果清理其它支出数据）
        if request.clean_other_expense:
            count = db.query(OtherExpense).delete()
            if count > 0:
                cleaned_items.append(f"其它支出({count}条)")
        
        # 删除系统配置（如果清理系统配置，包括初期现金）
        if request.clean_system_config:
            count = db.query(SystemConfig).delete()
            if count > 0:
                cleaned_items.append(f"系统配置({count}条)")
        
        # 删除操作日志（如果清理操作日志）
        if request.clean_operation_logs:
            count = db.query(OperationLog).delete()
            if count > 0:
                cleaned_items.append(f"操作日志({count}条)")
        
        # 删除用户（如果清理用户数据，默认不清理）
        if request.clean_users:
            count = db.query(User).delete()
            if count > 0:
                cleaned_items.append(f"用户({count}条)")
        
        db.commit()
        
        return {
            "message": "数据清理成功",
            "backup_file": backup_filename,
            "cleaned_items": cleaned_items
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.post("/upload")
async def upload_backup(file: UploadFile = File(...)):
    """上传备份文件"""
    try:
        if not file.filename.endswith('.db'):
            raise HTTPException(status_code=400, detail="只能上传.db文件")
        
        # 保存上传的文件到备份目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"upload_backup_{timestamp}_{file.filename}"
        backup_path = BACKUP_DIR / backup_filename
        
        with open(backup_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "message": "上传成功",
            "filename": backup_filename,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

