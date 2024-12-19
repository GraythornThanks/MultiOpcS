from typing import List, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应模型"""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

class ServerInfo(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True

class NodeInfo(BaseModel):
    id: int
    name: str
    node_id: str
    
    class Config:
        from_attributes = True 