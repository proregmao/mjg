"""
供货商模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Supplier(Base):
    """供货商表"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True, comment="供货商名称")
    contact = Column(String(50), comment="联系人")
    phone = Column(String(20), index=True, comment="联系电话")
    address = Column(String(255), comment="地址")
    notes = Column(String(500), comment="备注")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关系
    purchases = relationship("Purchase", back_populates="supplier")

    __table_args__ = (
        Index("idx_suppliers_name", "name"),
        Index("idx_suppliers_phone", "phone"),
    )

