"""
数据库初始化脚本
"""
from app.db.database import engine, Base
from app.models import (
    Customer, Product, Room, RoomSession, RoomCustomer,
    CustomerLoan, CustomerRepayment, Transfer,
    ProductConsumption, MealRecord, RoomTransfer
)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成！")


if __name__ == "__main__":
    init_db()

























