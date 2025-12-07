"""
数据库模型
"""
from app.models.customer import Customer
from app.models.product import Product
from app.models.room import Room
from app.models.room_session import RoomSession
from app.models.room_customer import RoomCustomer
from app.models.customer_loan import CustomerLoan
from app.models.customer_repayment import CustomerRepayment
from app.models.transfer import Transfer
from app.models.product_consumption import ProductConsumption
from app.models.meal_record import MealRecord
from app.models.room_transfer import RoomTransfer
from app.models.user import User
from app.models.supplier import Supplier
from app.models.purchase import Purchase, PurchaseItem

__all__ = [
    "Customer",
    "Product",
    "Room",
    "RoomSession",
    "RoomCustomer",
    "CustomerLoan",
    "CustomerRepayment",
    "Transfer",
    "ProductConsumption",
    "MealRecord",
    "RoomTransfer",
    "User",
    "Supplier",
    "Purchase",
    "PurchaseItem",
]















