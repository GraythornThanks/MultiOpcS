from pydantic import BaseModel, Field, constr, validator
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum
import re

class ServerStatus(str, Enum):
    STOPPED = "stopped"    # 服务器已停止
    STARTING = "starting"  # 服务器正在启动
    RUNNING = "running"    # 服务器正在运行
    ERROR = "error"       # 服务器出错

class DataType(str, Enum):
    UINT16 = "UINT16"
    UINT32 = "UINT32"
    UINT64 = "UINT64"
    INT32 = "INT32"
    INT64 = "INT64"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    STRING = "STRING"
    BYTESTRING = "BYTESTRING"
    CHAR = "CHAR"
    BOOL = "BOOL"
    DATETIME = "DATETIME"

# ISO 8601 日期时间格式的正则表达式
ISO_DATETIME_PATTERN = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$'

# Node Schemas
class AccessLevel(str, Enum):
    READ = "READ"         # 只读
    WRITE = "WRITE"       # 只写
    READWRITE = "READWRITE"  # 读写

class NodeBase(BaseModel):
    name: str
    node_id: str
    data_type: DataType
    access_level: AccessLevel
    description: Optional[str] = None
    initial_value: Optional[str] = None

    @validator('initial_value')
    def validate_initial_value(cls, v, values):
        if v is None:
            return v
            
        data_type = values.get('data_type')
        if not data_type:
            return v
            
        try:
            if data_type == DataType.UINT16:
                val = int(v)
                if not (0 <= val <= 65535):
                    raise ValueError("UINT16 must be between 0 and 65535")
            elif data_type == DataType.UINT32:
                val = int(v)
                if not (0 <= val <= 4294967295):
                    raise ValueError("UINT32 must be between 0 and 4294967295")
            elif data_type == DataType.UINT64:
                val = int(v)
                if not (0 <= val <= 18446744073709551615):
                    raise ValueError("UINT64 must be between 0 and 18446744073709551615")
            elif data_type == DataType.INT32:
                val = int(v)
                if not (-2147483648 <= val <= 2147483647):
                    raise ValueError("INT32 must be between -2147483648 and 2147483647")
            elif data_type == DataType.INT64:
                val = int(v)
                if not (-9223372036854775808 <= val <= 9223372036854775807):
                    raise ValueError("INT64 must be between -9223372036854775808 and 9223372036854775807")
            elif data_type in (DataType.FLOAT, DataType.DOUBLE):
                float(v)
            elif data_type == DataType.BOOL:
                if v.lower() not in ('true', 'false', '1', '0'):
                    raise ValueError("BOOL must be true/false or 1/0")
            elif data_type == DataType.CHAR:
                if len(v) != 1:
                    raise ValueError("CHAR must be a single character")
            elif data_type == DataType.DATETIME:
                # 验证 ISO 8601 格式
                if not re.match(ISO_DATETIME_PATTERN, v):
                    raise ValueError("DATETIME must be in ISO 8601 format (e.g., 2023-06-12T16:31:34.000Z)")
                # 尝试解析日期时间
                datetime.strptime(v.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError as e:
            raise ValueError(f"Invalid initial value for type {data_type}: {str(e)}")
        return v

class NodeCreate(NodeBase):
    serverIds: Optional[List[int]] = None

class NodeUpdate(BaseModel):
    name: Optional[str] = None
    node_id: Optional[str] = None
    data_type: Optional[DataType] = None
    access_level: Optional[AccessLevel] = None
    description: Optional[str] = None
    initial_value: Optional[str] = None
    serverIds: Optional[List[int]] = None

    @validator('initial_value')
    def validate_initial_value(cls, v, values):
        if v is None:
            return v
            
        data_type = values.get('data_type')
        if not data_type:
            return v
            
        try:
            if data_type == DataType.UINT16:
                val = int(v)
                if not (0 <= val <= 65535):
                    raise ValueError("UINT16 must be between 0 and 65535")
            elif data_type == DataType.UINT32:
                val = int(v)
                if not (0 <= val <= 4294967295):
                    raise ValueError("UINT32 must be between 0 and 4294967295")
            elif data_type == DataType.UINT64:
                val = int(v)
                if not (0 <= val <= 18446744073709551615):
                    raise ValueError("UINT64 must be between 0 and 18446744073709551615")
            elif data_type == DataType.INT32:
                val = int(v)
                if not (-2147483648 <= val <= 2147483647):
                    raise ValueError("INT32 must be between -2147483648 and 2147483647")
            elif data_type == DataType.INT64:
                val = int(v)
                if not (-9223372036854775808 <= val <= 9223372036854775807):
                    raise ValueError("INT64 must be between -9223372036854775808 and 9223372036854775807")
            elif data_type in (DataType.FLOAT, DataType.DOUBLE):
                float(v)
            elif data_type == DataType.BOOL:
                if v.lower() not in ('true', 'false', '1', '0'):
                    raise ValueError("BOOL must be true/false or 1/0")
            elif data_type == DataType.CHAR:
                if len(v) != 1:
                    raise ValueError("CHAR must be a single character")
            elif data_type == DataType.DATETIME:
                # 验证 ISO 8601 格式
                if not re.match(ISO_DATETIME_PATTERN, v):
                    raise ValueError("DATETIME must be in ISO 8601 format (e.g., 2023-06-12T16:31:34.000Z)")
                # 尝试解析日期时间
                datetime.strptime(v.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError as e:
            raise ValueError(f"Invalid initial value for type {data_type}: {str(e)}")
        return v

class Node(NodeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    servers: List['OPCUAServerInfo'] = []

    class Config:
        from_attributes = True

# OPCUAServer Schemas
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

class OPCUAServerInfo(BaseModel):
    id: int
    name: str
    port: int
    endpoint: Optional[str] = None
    status: ServerStatus
    last_started: Optional[datetime] = None

    class Config:
        from_attributes = True

class NodeInfo(BaseModel):
    id: int
    name: str
    node_id: str
    data_type: DataType
    access_level: AccessLevel

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

class NodeBatchCreate(BaseModel):
    """批量创建节点的请求模型"""
    name_pattern: str = Field(..., description="节点名称模式，使用{n}作为序号占位符")
    node_id_pattern: str = Field(..., description="节点ID模式，使用{n}作为序号占位符")
    count: int = Field(..., gt=0, le=100, description="要创建的节点数量")
    data_type: DataType
    access_level: AccessLevel
    description: Optional[str] = None
    initial_value: Optional[str] = None
    serverIds: Optional[List[int]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name_pattern": "tube{n}",
                "node_id_pattern": "ns=2;s=Device1.Tube{n}",
                "count": 3,
                "data_type": "FLOAT",
                "access_level": "READWRITE",
                "description": "温度传感器",
                "initial_value": "25.0",
                "serverIds": [1]
            }
        } 