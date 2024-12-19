from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .enums import ServerStatus
from .common import NodeInfo

class ServerInfo(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True

class OPCUAServerBase(BaseModel):
    name: str
    port: int = Field(ge=1024, le=65535)  # 有效的端口范围
    endpoint: Optional[str] = None

class OPCUAServerCreate(OPCUAServerBase):
    nodeIds: Optional[List[int]] = None

class OPCUAServerUpdate(BaseModel):
    name: Optional[str] = None
    port: Optional[int] = Field(None, ge=1024, le=65535)
    endpoint: Optional[str] = None
    nodeIds: Optional[List[int]] = None

class OPCUAServerInfo(OPCUAServerBase):
    id: int
    status: ServerStatus
    last_started: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    nodes: List[NodeInfo] = []

    class Config:
        from_attributes = True

class OPCUAServer(OPCUAServerBase):
    id: int
    status: ServerStatus
    last_started: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    nodes: List[NodeInfo] = []

    class Config:
        from_attributes = True