"""
操作日志模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from app.db.database import Base


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True, comment="用户ID")
    username = Column(String(100), nullable=False, index=True, comment="用户名")
    action = Column(String(100), nullable=False, index=True, comment="操作类型：如创建客户、删除商品等")
    module = Column(String(50), nullable=False, index=True, comment="操作模块：如客户管理、商品管理等")
    method = Column(String(10), nullable=False, comment="HTTP方法：GET、POST、PUT、DELETE")
    path = Column(String(500), nullable=False, comment="请求路径")
    ip_address = Column(String(50), comment="IP地址")
    user_agent = Column(String(500), comment="用户代理")
    request_data = Column(Text, comment="请求数据（JSON格式）")
    response_data = Column(Text, comment="响应数据（JSON格式，仅记录关键信息）")
    status_code = Column(Integer, comment="HTTP状态码")
    error_message = Column(Text, comment="错误信息（如果有）")
    execution_time = Column(Integer, comment="执行时间（毫秒）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, comment="创建时间")

    __table_args__ = (
        Index("idx_operation_logs_user_id", "user_id"),
        Index("idx_operation_logs_username", "username"),
        Index("idx_operation_logs_action", "action"),
        Index("idx_operation_logs_module", "module"),
        Index("idx_operation_logs_created_at", "created_at"),
    )








