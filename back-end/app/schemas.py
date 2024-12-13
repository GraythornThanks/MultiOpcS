from pydantic import BaseModel, Field, constr, validator, model_validator
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
from enum import Enum
import re
from . import models

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

class ValueChangeType(str, Enum):
    NONE = "none"           # 不自动变化
    LINEAR = "linear"       # 线性变化
    DISCRETE = "discrete"   # 离散值变化
    RANDOM = "random"       # 随机变化
    CONDITIONAL = "conditional"  # 条件变化

class LinearChangeConfig(BaseModel):
    min_value: float
    max_value: float
    update_interval: int  # 更新间隔（毫秒）
    step_size: float
    random_interval: bool = False  # 是否随机更新间隔
    random_step: bool = False      # 是否随机步长
    reset_on_bounds: bool = True   # 到达边界是否重置

class DiscreteChangeConfig(BaseModel):
    values: List[str]  # 值列表
    update_interval: int  # 更新间隔（毫秒）
    random_interval: bool = False  # 是否随机更新间隔

class RandomChangeConfig(BaseModel):
    min_value: float
    max_value: float
    update_interval: int  # 更新间隔（毫秒）
    random_interval: bool = False  # 是否随机更新间隔

class ConditionalChangeConfig(BaseModel):
    trigger_node_id: str  # 触发节点的ID
    trigger_value: str    # 触发值
    change_value: str     # 变化值

class NodeBase(BaseModel):
    name: str
    node_id: str
    data_type: DataType
    access_level: AccessLevel
    description: Optional[str] = None
    initial_value: Optional[str] = None
    value_change_type: Optional[ValueChangeType] = ValueChangeType.NONE
    value_change_config: Optional[Dict[str, Any]] = None
    value_precision: Optional[int] = None

    @model_validator(mode='after')
    def validate_value_change_config(self) -> 'NodeBase':
        change_type = self.value_change_type
        config = self.value_change_config
        data_type = self.data_type

        if change_type == ValueChangeType.NONE:
            if config is not None:
                raise ValueError("Value change config should be None when change type is NONE")
            return self

        if change_type and config is None:
            raise ValueError(f"Value change config is required for change type {change_type}")

        # 验证数值类型
        numeric_types = [DataType.INT32, DataType.INT64, DataType.UINT16, 
                        DataType.UINT32, DataType.UINT64, DataType.FLOAT, 
                        DataType.DOUBLE]

        try:
            if change_type == ValueChangeType.LINEAR:
                if data_type not in numeric_types:
                    raise ValueError("Linear change only supports numeric types")
                LinearChangeConfig(**config)
            
            elif change_type == ValueChangeType.DISCRETE:
                DiscreteChangeConfig(**config)
                # 验证值列表中的值是否符合数据类型
                for value in config['values']:
                    self.validate_value_for_type(value, data_type)
            
            elif change_type == ValueChangeType.RANDOM:
                if data_type not in numeric_types:
                    raise ValueError("Random change only supports numeric types")
                RandomChangeConfig(**config)
            
            elif change_type == ValueChangeType.CONDITIONAL:
                ConditionalChangeConfig(**config)
                # 验证变化值是否符合数据类型
                self.validate_value_for_type(config['change_value'], data_type)
        
        except ValueError as e:
            raise ValueError(f"Invalid configuration for {change_type}: {str(e)}")
        
        return self

    @classmethod
    def validate_value_for_type(cls, value: str, data_type: DataType):
        try:
            if data_type == DataType.UINT16:
                val = int(value)
                if not (0 <= val <= 65535):
                    raise ValueError("UINT16 must be between 0 and 65535")
            elif data_type == DataType.UINT32:
                val = int(value)
                if not (0 <= val <= 4294967295):
                    raise ValueError("UINT32 must be between 0 and 4294967295")
            elif data_type == DataType.UINT64:
                val = int(value)
                if not (0 <= val <= 18446744073709551615):
                    raise ValueError("UINT64 must be between 0 and 18446744073709551615")
            elif data_type == DataType.INT32:
                val = int(value)
                if not (-2147483648 <= val <= 2147483647):
                    raise ValueError("INT32 must be between -2147483648 and 2147483647")
            elif data_type == DataType.INT64:
                val = int(value)
                if not (-9223372036854775808 <= val <= 9223372036854775807):
                    raise ValueError("INT64 must be between -9223372036854775808 and 9223372036854775807")
            elif data_type in (DataType.FLOAT, DataType.DOUBLE):
                float(value)
            elif data_type == DataType.BOOL:
                if value.lower() not in ('true', 'false', '1', '0'):
                    raise ValueError("BOOL must be true/false or 1/0")
            elif data_type == DataType.CHAR:
                if len(value) != 1:
                    raise ValueError("CHAR must be a single character")
            elif data_type == DataType.DATETIME:
                if not re.match(ISO_DATETIME_PATTERN, value):
                    raise ValueError("DATETIME must be in ISO 8601 format")
                datetime.strptime(value.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError as e:
            raise ValueError(f"Invalid value for type {data_type}: {str(e)}")

class NodeCreate(BaseModel):
    """创建节点的请求模型"""
    name: str
    node_id: str
    data_type: models.DataType
    access_level: models.AccessLevel
    description: Optional[str] = None
    initial_value: Optional[str] = None
    value_change_type: models.ValueChangeType = models.ValueChangeType.NONE
    value_change_config: Optional[Dict[str, Any]] = None
    value_precision: Optional[int] = None
    serverIds: Optional[List[int]] = None

    @model_validator(mode='after')
    def validate_node_config(self) -> 'NodeCreate':
        """验证节点配置"""
        try:
            # 验证值变化配置
            if self.value_change_type != models.ValueChangeType.NONE:
                if not self.value_change_config:
                    raise ValueError("值变化类型需要配置")

                # 验证数值类型
                numeric_types = [
                    models.DataType.INT32, models.DataType.INT64, models.DataType.UINT16,
                    models.DataType.UINT32, models.DataType.UINT64, models.DataType.FLOAT,
                    models.DataType.DOUBLE
                ]

                if self.value_change_type == models.ValueChangeType.LINEAR:
                    if self.data_type not in numeric_types:
                        raise ValueError("线性变化只支持数值类型")
                    required_fields = ['min_value', 'max_value', 'update_interval', 'step_size']
                    for field in required_fields:
                        if field not in self.value_change_config:
                            raise ValueError(f"线性变化配置缺少必要字段: {field}")
                    
                    # 验证字段类型
                    try:
                        float(self.value_change_config['min_value'])
                        float(self.value_change_config['max_value'])
                        int(self.value_change_config['update_interval'])
                        float(self.value_change_config['step_size'])
                    except (ValueError, TypeError):
                        raise ValueError("线性变化配置的字段类型不正确")

                elif self.value_change_type == models.ValueChangeType.DISCRETE:
                    if 'values' not in self.value_change_config:
                        raise ValueError("离散变化配置缺少值列表")
                    if 'update_interval' not in self.value_change_config:
                        raise ValueError("离散变化配置缺少更新间隔")
                    
                    # 验证值列表
                    if not isinstance(self.value_change_config['values'], list):
                        raise ValueError("离散变化的值列表必须是数组")
                    for value in self.value_change_config['values']:
                        self.validate_value_for_type(str(value), self.data_type)

                elif self.value_change_type == models.ValueChangeType.RANDOM:
                    if self.data_type not in numeric_types:
                        raise ValueError("随机变化只支持数值类型")
                    required_fields = ['min_value', 'max_value', 'update_interval']
                    for field in required_fields:
                        if field not in self.value_change_config:
                            raise ValueError(f"随机变化配置缺少必要字段: {field}")
                    
                    # 验证字段类型
                    try:
                        float(self.value_change_config['min_value'])
                        float(self.value_change_config['max_value'])
                        int(self.value_change_config['update_interval'])
                    except (ValueError, TypeError):
                        raise ValueError("随机变化配置的字段类型不正确")

                elif self.value_change_type == models.ValueChangeType.CONDITIONAL:
                    required_fields = ['trigger_node_id', 'trigger_value', 'change_value']
                    for field in required_fields:
                        if field not in self.value_change_config:
                            raise ValueError(f"条件变化配置缺少必要字段: {field}")
                    
                    # 验证触发值和变化值是否符合数据类型
                    self.validate_value_for_type(
                        str(self.value_change_config['trigger_value']),
                        self.data_type
                    )
                    self.validate_value_for_type(
                        str(self.value_change_config['change_value']),
                        self.data_type
                    )

            # 验证数值精度
            if self.value_precision is not None:
                if self.data_type not in [models.DataType.FLOAT, models.DataType.DOUBLE]:
                    raise ValueError("只有浮点数类型可以设置精度")
                if not (0 <= self.value_precision <= 10):
                    raise ValueError("精度必须在0到10之间")

            return self
        except Exception as e:
            print(f"验证错误: {str(e)}")  # 添加调试日志
            raise ValueError(str(e))

    @classmethod
    def validate_value_for_type(cls, value: str, data_type: models.DataType) -> None:
        """验证值是否符合数据类型"""
        try:
            if data_type == models.DataType.UINT16:
                val = int(value)
                if not (0 <= val <= 65535):
                    raise ValueError("UINT16 的值必须在 0 到 65535 之间")
            elif data_type == models.DataType.UINT32:
                val = int(value)
                if not (0 <= val <= 4294967295):
                    raise ValueError("UINT32 的值必须在 0 到 4294967295 之间")
            elif data_type == models.DataType.UINT64:
                val = int(value)
                if not (0 <= val <= 18446744073709551615):
                    raise ValueError("UINT64 的值超出范围")
            elif data_type == models.DataType.INT32:
                val = int(value)
                if not (-2147483648 <= val <= 2147483647):
                    raise ValueError("INT32 的值必须在 -2147483648 到 2147483647 之间")
            elif data_type == models.DataType.INT64:
                val = int(value)
                if not (-9223372036854775808 <= val <= 9223372036854775807):
                    raise ValueError("INT64 的值超出范围")
            elif data_type in (models.DataType.FLOAT, models.DataType.DOUBLE):
                float(value)
            elif data_type == models.DataType.BOOL:
                if value.lower() not in ('true', 'false', '1', '0'):
                    raise ValueError("布尔值必须是 true/false 或 1/0")
            elif data_type == models.DataType.CHAR:
                if len(value) != 1:
                    raise ValueError("字符类型必须是单个字符")
            elif data_type == models.DataType.DATETIME:
                if not re.match(ISO_DATETIME_PATTERN, value):
                    raise ValueError("日期时间必须符合 ISO 8601 格式")
                datetime.strptime(value.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError as e:
            raise ValueError(f"值类型验证失败: {str(e)}")

class NodeUpdate(BaseModel):
    name: Optional[str] = None
    node_id: Optional[str] = None
    data_type: Optional[DataType] = None
    access_level: Optional[AccessLevel] = None
    description: Optional[str] = None
    initial_value: Optional[str] = None
    value_change_type: Optional[ValueChangeType] = None
    value_change_config: Optional[Dict[str, Any]] = None
    value_precision: Optional[int] = None
    serverIds: Optional[List[int]] = None

    @model_validator(mode='after')
    def validate_value_change_config(self) -> 'NodeUpdate':
        change_type = self.value_change_type
        config = self.value_change_config
        data_type = self.data_type

        if change_type is None or config is None:
            return self

        if change_type == ValueChangeType.NONE:
            if config is not None:
                raise ValueError("Value change config should be None when change type is NONE")
            return self

        # 验证数值类型
        numeric_types = [DataType.INT32, DataType.INT64, DataType.UINT16, 
                        DataType.UINT32, DataType.UINT64, DataType.FLOAT, 
                        DataType.DOUBLE]

        try:
            if change_type == ValueChangeType.LINEAR:
                if data_type and data_type not in numeric_types:
                    raise ValueError("Linear change only supports numeric types")
                LinearChangeConfig(**config)
            
            elif change_type == ValueChangeType.DISCRETE:
                DiscreteChangeConfig(**config)
                # 验证值列表中的值是否符合数据类型
                if data_type:
                    for value in config['values']:
                        NodeBase.validate_value_for_type(value, data_type)
            
            elif change_type == ValueChangeType.RANDOM:
                if data_type and data_type not in numeric_types:
                    raise ValueError("Random change only supports numeric types")
                RandomChangeConfig(**config)
            
            elif change_type == ValueChangeType.CONDITIONAL:
                ConditionalChangeConfig(**config)
                # 验证变化值是否符合数据类型
                if data_type:
                    NodeBase.validate_value_for_type(config['change_value'], data_type)
        
        except ValueError as e:
            raise ValueError(f"Invalid configuration for {change_type}: {str(e)}")
        
        return self

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