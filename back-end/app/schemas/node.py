from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .enums import DataType, AccessLevel, ValueChangeType
from .common import ServerInfo, PaginatedResponse

class NodeBase(BaseModel):
    name: str
    node_id: str
    data_type: DataType
    access_level: AccessLevel = AccessLevel.READWRITE
    description: Optional[str] = None
    initial_value: Optional[str] = None
    value_change_type: ValueChangeType = ValueChangeType.NONE
    value_change_config: Optional[Dict[str, Any]] = None
    value_precision: Optional[int] = Field(None, ge=0, le=10)

class NodeCreate(NodeBase):
    serverIds: Optional[List[int]] = None

class NodeUpdate(BaseModel):
    name: Optional[str] = None
    node_id: Optional[str] = None
    data_type: Optional[DataType] = None
    access_level: Optional[AccessLevel] = None
    description: Optional[str] = None
    initial_value: Optional[str] = None
    value_change_type: Optional[ValueChangeType] = None
    value_change_config: Optional[Dict[str, Any]] = None
    value_precision: Optional[int] = Field(None, ge=0, le=10)
    serverIds: Optional[List[int]] = None

class Node(NodeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    servers: List[ServerInfo] = []

    class Config:
        from_attributes = True

class PaginatedNodes(PaginatedResponse[Node]):
    """节点分页响应模型"""
    pass 