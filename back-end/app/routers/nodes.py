from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Tuple
from datetime import datetime
import re
from ..database import get_db
from .. import models
from ..schemas import node as node_schema
from ..models.enums import DataType, ValueChangeType

router = APIRouter(
    prefix="/nodes",
    tags=["nodes"],
    responses={404: {"description": "Not found"}},
)

# 节点ID格式验证
def validate_node_id(node_id: str) -> bool:
    node_id_pattern = re.compile(r'^(ns=\d+;)?[isb]=.+$')
    return bool(node_id_pattern.match(node_id))

# 初始值验证
def validate_initial_value(value: Optional[str], data_type: models.DataType) -> tuple[bool, str]:
    if not value:
        return True, ""
        
    try:
        if data_type == models.DataType.BOOL:
            if value.lower() not in ['true', 'false']:
                return False, "布尔值必须是 true 或 false"
        elif data_type == models.DataType.CHAR:
            if len(value) != 1:
                return False, "字符类型必须是单个字符"
        elif data_type == models.DataType.INT32:
            val = int(value)
            if val < -2147483648 or val > 2147483647:
                return False, "INT32 的值必须在 -2147483648 到 2147483647 之间"
        elif data_type == models.DataType.INT64:
            val = int(value)
            if val < -9223372036854775808 or val > 9223372036854775807:
                return False, "INT64 的值超出范围"
        elif data_type == models.DataType.UINT16:
            val = int(value)
            if val < 0 or val > 65535:
                return False, "UINT16 的值必须在 0 到 65535 之间"
        elif data_type == models.DataType.UINT32:
            val = int(value)
            if val < 0 or val > 4294967295:
                return False, "UINT32 的值必须在 0 到 4294967295 之间"
        elif data_type == models.DataType.UINT64:
            val = int(value)
            if val < 0 or val > 18446744073709551615:
                return False, "UINT64 的值超出范围"
        elif data_type == models.DataType.FLOAT or data_type == models.DataType.DOUBLE:
            float(value)  # 验证否为有效的浮点数
        elif data_type == models.DataType.DATETIME:
            # 验证ISO 8601格式
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$', value):
                return False, "日期时间必须符合 ISO 8601 格式 (YYYY-MM-DDThh:mm:ss.sssZ)"
            try:
                datetime.strptime(value.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                return False, "无效的日期时间"
        return True, ""
    except ValueError as e:
        return False, str(e)

def parse_node_pattern(name: str, node_id: str) -> List[Tuple[str, str]]:
    """解析节点名称和ID中的占位符模式，返回展开后的节点名称和ID列表"""
    # 查找模式 {n} 或 {start-end}
    pattern = r'\{(\d+)(?:-(\d+))?\}'
    name_match = re.search(pattern, name)
    node_id_match = re.search(pattern, node_id)
    
    if not name_match and not node_id_match:
        return [(name, node_id)]
        
    results = []
    
    if name_match:
        start = int(name_match.group(1))
        end = int(name_match.group(2)) if name_match.group(2) else start
    else:
        # 如果称中没有占位符，使用节点ID中的范围
        start = int(node_id_match.group(1))
        end = int(node_id_match.group(2)) if node_id_match.group(2) else start
        
    for i in range(start, end + 1):
        expanded_name = re.sub(pattern, str(i), name)
        expanded_node_id = re.sub(pattern, str(i), node_id)
        results.append((expanded_name, expanded_node_id))
        
    return results

@router.get("/", response_model=node_schema.PaginatedNodes)
def get_nodes(
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: int = Query(default=10, ge=1, le=100, description="每页记录数"),
    db: Session = Depends(get_db)
):
    """获取节点列表，支持分页"""
    try:
        # 使用子查询优化性能
        total = db.query(models.Node).count()
        print(f"[INFO] 总节点数: {total}")
        
        # 优化查询，只获取必要的字段
        nodes = (
            db.query(models.Node)
            .options(
                joinedload(models.Node.servers).load_only(
                    models.OPCUAServer.id,
                    models.OPCUAServer.name
                )
            )
            .order_by(models.Node.id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        print(f"[INFO] 成功获取节点列表: 偏移量={skip}, 限制={limit}, 返回数量={len(nodes)}")
        
        # 构建分页响应
        response = {
            "total": total,
            "items": nodes,
            "page": skip // limit + 1,
            "size": limit,
            "pages": (total + limit - 1) // limit
        }
        
        return response
        
    except Exception as e:
        print(f"[ERROR] 获取节点列表失败: {str(e)}")
        # 记录详细的错误信息
        import traceback
        print(f"[ERROR] 详细错误信息: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "获取节点列表失败",
                "error": str(e)
            }
        )

@router.get("/{node_id}", response_model=node_schema.Node)
def get_node(node_id: int, db: Session = Depends(get_db)):
    """获取单个节点详情"""
    node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node

@router.post("/", response_model=node_schema.Node)
def create_node(node: node_schema.NodeCreate, db: Session = Depends(get_db)):
    """创建新节点"""
    try:
        # 验证节点ID格式
        if not validate_node_id(node.node_id):
            raise HTTPException(status_code=400, detail="节点ID格式无效")
        
        # 检查节点ID是否已存在
        existing_node = db.query(models.Node).filter(models.Node.node_id == node.node_id).first()
        if existing_node:
            raise HTTPException(status_code=400, detail="节点ID已存在")
        
        # 验证初始值
        if node.initial_value:
            is_valid, error_message = validate_initial_value(node.initial_value, node.data_type)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"初始值无效: {error_message}")
        
        # 验证值变化配置
        if node.value_change_type != models.ValueChangeType.NONE and not node.value_change_config:
            raise HTTPException(status_code=400, detail="值变化类型需要配置")
        
        # 验证数值精度
        if node.value_precision is not None:
            if node.data_type not in [models.DataType.FLOAT, models.DataType.DOUBLE]:
                raise HTTPException(status_code=400, detail="只有浮点数类型可以设置精度")
            if not (0 <= node.value_precision <= 10):
                raise HTTPException(status_code=400, detail="精度必须在0到10之间")
        
        # 创建新节点
        db_node = models.Node(
            name=node.name,
            node_id=node.node_id,
            data_type=node.data_type,
            access_level=node.access_level,
            description=node.description,
            initial_value=node.initial_value,
            value_change_type=node.value_change_type,
            value_change_config=node.value_change_config,
            value_precision=node.value_precision
        )
        
        # 如果指定了服务器ID，建立关联
        if node.serverIds:
            servers = db.query(models.OPCUAServer).filter(
                models.OPCUAServer.id.in_(node.serverIds)
            ).all()
            if len(servers) != len(node.serverIds):
                raise HTTPException(status_code=400, detail="一个或多个服务器ID不存在")
            db_node.servers = servers
        
        try:
            db.add(db_node)
            db.commit()
            db.refresh(db_node)
            return db_node
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"保存节点失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建节点失败: {str(e)}")

@router.put("/{node_id}", response_model=node_schema.Node)
def update_node(node_id: int, node: node_schema.NodeUpdate, db: Session = Depends(get_db)):
    """更新节点信息"""
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # 如果更新节点ID，验证格式和唯一性
    if node.node_id is not None:
        if not validate_node_id(node.node_id):
            raise HTTPException(status_code=400, detail="Invalid node ID format")
        existing_node = db.query(models.Node).filter(
            models.Node.node_id == node.node_id,
            models.Node.id != node_id
        ).first()
        if existing_node:
            raise HTTPException(status_code=400, detail="Node ID already registered")
    
    # 更新节点属性
    update_data = node.dict(exclude_unset=True)
    
    # 如果包含serverIds，更新服务器关联
    if "serverIds" in update_data:
        serverIds = update_data.pop("serverIds")
        if serverIds is not None:
            servers = db.query(models.OPCUAServer).filter(
                models.OPCUAServer.id.in_(serverIds)
            ).all()
            if len(servers) != len(serverIds):
                raise HTTPException(status_code=400, detail="One or more server IDs not found")
            db_node.servers = servers
    
    try:
        for key, value in update_data.items():
            setattr(db_node, key, value)
        db.commit()
        db.refresh(db_node)
        return db_node
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{node_id}")
def delete_node(node_id: int, db: Session = Depends(get_db)):
    """删除节点"""
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    
    db.delete(db_node)
    db.commit()
    return {"ok": True}