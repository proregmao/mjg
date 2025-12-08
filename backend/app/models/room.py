"""
房间模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Room(Base):
    """房间表"""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, comment="名称")
    status = Column(String(20), default="idle", comment="状态：idle=空闲, in_use=使用中, settled=已结算")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关系
    sessions = relationship("RoomSession", back_populates="room")

    __table_args__ = (
        Index("idx_rooms_name", "name"),
    )


















