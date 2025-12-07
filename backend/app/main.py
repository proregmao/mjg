"""
FastAPI主应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.db.database import engine, Base
import traceback

# 导入所有模型以确保表被创建
from app.models import (
    Customer, Product, Room, RoomSession, RoomCustomer,
    CustomerLoan, CustomerRepayment, Transfer,
    ProductConsumption, MealRecord, RoomTransfer, User,
    Supplier, Purchase, PurchaseItem
)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title="麻将馆记账系统API",
    description="麻将馆记账管理系统后端API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，确保所有错误都返回CORS头"""
    import traceback
    error_detail = str(exc)
    traceback_str = traceback.format_exc()
    print(f"未处理的异常: {error_detail}")
    print(traceback_str)
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"内部服务器错误: {error_detail}",
            "traceback": traceback_str if app.debug else None
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/")
async def root():
    """根路径"""
    return {"message": "麻将馆记账系统API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# 注册API路由
from app.api import customers, products, rooms, statistics, export, auth, backup, users, suppliers, purchases
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(rooms.router)
app.include_router(statistics.router)
app.include_router(export.router)
app.include_router(backup.router)
app.include_router(users.router)
app.include_router(suppliers.router)
app.include_router(purchases.router)

