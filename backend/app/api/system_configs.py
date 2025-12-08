"""
系统配置管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.system_config import SystemConfig
from app.schemas.system_config import (
    SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse
)

router = APIRouter(prefix="/api/system-configs", tags=["系统配置"])


@router.get("", response_model=List[SystemConfigResponse])
def get_system_configs(db: Session = Depends(get_db)):
    """获取所有系统配置"""
    configs = db.query(SystemConfig).all()
    return configs


@router.get("/{config_key}", response_model=SystemConfigResponse)
def get_system_config(config_key: str, db: Session = Depends(get_db)):
    """获取系统配置"""
    config = db.query(SystemConfig).filter(SystemConfig.key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.post("", response_model=SystemConfigResponse)
def create_system_config(config: SystemConfigCreate, db: Session = Depends(get_db)):
    """创建系统配置"""
    # 检查是否已存在
    existing = db.query(SystemConfig).filter(SystemConfig.key == config.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="配置键已存在")
    
    db_config = SystemConfig(
        key=config.key,
        value=config.value,
        description=config.description
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


@router.put("/{config_key}", response_model=SystemConfigResponse)
def update_system_config(
    config_key: str,
    config: SystemConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新系统配置（如果不存在则创建）"""
    db_config = db.query(SystemConfig).filter(SystemConfig.key == config_key).first()
    if not db_config:
        # 如果不存在，则创建
        db_config = SystemConfig(
            key=config_key,
            value=config.value or "",
            description=config.description
        )
        db.add(db_config)
    else:
        # 如果存在，则更新
        if config.value is not None:
            db_config.value = config.value
        if config.description is not None:
            db_config.description = config.description
    
    db.commit()
    db.refresh(db_config)
    return db_config


@router.delete("/{config_key}")
def delete_system_config(config_key: str, db: Session = Depends(get_db)):
    """删除系统配置"""
    config = db.query(SystemConfig).filter(SystemConfig.key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    db.delete(config)
    db.commit()
    return {"message": "配置已删除"}


