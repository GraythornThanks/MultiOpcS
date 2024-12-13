from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table, Enum, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import enum

class ServerStatus(enum.Enum):
    STOPPED = "stopped"    # 服务器已停止
    STARTING = "starting"  # 服务器正在启动
    RUNNING = "running"    # 服务器正在运行
    ERROR = "error"       # 服务器出错

class DataType(enum.Enum):
    # 基本数值类型
    UINT16 = "UINT16"     # 16位无符号整数
    UINT32 = "UINT32"     # 32位无符号整数
    UINT64 = "UINT64"     # 64位无符号整数
    INT32 = "INT32"       # 32位有符号整数
    INT64 = "INT64"       # 64位有符号整数
    FLOAT = "FLOAT"       # 单精度浮点数
    DOUBLE = "DOUBLE"     # 双精度浮点数
    BOOL = "BOOL"         # 布尔值
    CHAR = "CHAR"         # 字符
    
    # 字符串和时间类型
    STRING = "STRING"          # 字符串
    DATETIME = "DATETIME"      # 日期时间
    BYTESTRING = "BYTESTRING"  # 字节字符串
    
    # OPC UA特定类型
    NODEID = "NODEID"              # 节点ID
    STATUSCODE = "STATUSCODE"      # 状态码
    LOCALIZEDTEXT = "LOCALIZEDTEXT" # 本地化文本
    QUALIFIEDNAME = "QUALIFIEDNAME" # 限定名称
    XMLELEMENT = "XMLELEMENT"      # XML元素
    VARIANT = "VARIANT"            # 变体类型
    DATAVALUE = "DATAVALUE"        # 数据值

class AccessLevel(enum.Enum):
    READ = "READ"         # 只读
    WRITE = "WRITE"       # 只写
    READWRITE = "READWRITE"  # 读写

class ValueChangeType(enum.Enum):
    NONE = "none"           # 不自动变化
    LINEAR = "linear"       # 线性变化
    DISCRETE = "discrete"   # 离散值变化
    RANDOM = "random"       # 随机变化
    CONDITIONAL = "conditional"  # 条件变化

# 服务器和节点的关联表
server_node_association = Table(
    'server_node_association',
    Base.metadata,
    Column('server_id', Integer, ForeignKey('opcua_servers.id', ondelete='CASCADE')),
    Column('node_id', Integer, ForeignKey('nodes.id', ondelete='CASCADE'))
)

class OPCUAServer(Base):
    __tablename__ = "opcua_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    endpoint = Column(String)  # 服务器监听地址，例如: opc.tcp://0.0.0.0:4840
    status = Column(Enum(ServerStatus), default=ServerStatus.STOPPED)
    port = Column(Integer)     # 服务器监听端口
    last_started = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 与节点的多对多关系
    nodes = relationship(
        "Node",
        secondary=server_node_association,
        back_populates="servers"
    )

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    node_id = Column(String, unique=True, index=True)  # OPC UA 节点ID
    data_type = Column(Enum(DataType))  # 数据类型
    access_level = Column(Enum(AccessLevel))  # 访问级别
    description = Column(String, nullable=True)
    initial_value = Column(String)  # 存储为字符串的初始值
    
    # 新增字段
    value_change_type = Column(Enum(ValueChangeType), default=ValueChangeType.NONE)  # 值变化类型
    value_change_config = Column(JSON, nullable=True)  # 值变化配置
    value_precision = Column(Integer, nullable=True)  # 数值精度（小数位数）
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 与服务器的多对多关系
    servers = relationship(
        "OPCUAServer",
        secondary=server_node_association,
        back_populates="nodes"
    ) 