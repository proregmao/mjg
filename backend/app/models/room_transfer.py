"""
房间转移记录模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class RoomTransfer(Base):
    """房间转移记录表"""
    __tablename__ = "room_transfers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("room_sessions.id"), nullable=False, comment="房间使用记录ID")
    from_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, comment="原房间ID")
    to_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, comment="目标房间ID")
    transferred_at = Column(DateTime(timezone=True), nullable=False, comment="转移时间")
    transferred_by = Column(String(100), comment="操作人")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    session = relationship("RoomSession", back_populates="room_transfers")
    from_room = relationship("Room", foreign_keys=[from_room_id])
    to_room = relationship("Room", foreign_keys=[to_room_id])


















