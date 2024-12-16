from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db
from sqlalchemy import func

router = APIRouter()

@router.get("/", response_model=schemas.PaginatedNodes)
def get_nodes(
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: int = Query(default=10, ge=1, le=100, description="每页记录数"),
    db: Session = Depends(get_db)
):
    """获取节点列表，支持分页"""
    # 获取总记录数
    total = db.query(func.count(models.Node.id)).scalar()
    
    # 获取分页数据
    nodes = db.query(models.Node)\
        .order_by(models.Node.id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return {
        "total": total,
        "items": nodes,
        "skip": skip,
        "limit": limit
    }

@router.post("/{node_id}/value-change", response_model=schemas.Node)
async def handle_node_value_change(
    node_id: int,
    trigger_node_id: int,
    db: Session = Depends(get_db)
):
    """处理节点值变化"""
    try:
        # 获取当前节点和触发节点
        node = db.query(models.Node).filter(models.Node.id == node_id).first()
        trigger_node = db.query(models.Node).filter(models.Node.id == trigger_node_id).first()
        
        if not node or not trigger_node:
            raise HTTPException(status_code=404, detail="Node not found")
            
        # 计算新值
        new_value = node.calculate_conditional_value(trigger_node.initial_value)
        
        if new_value is not None:
            # 更新节点值
            node.initial_value = new_value
            db.commit()
            db.refresh(node)
            
        return node
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error handling value change: {str(e)}") 