from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Enum as SQLEnum, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from .enums import ServerStatus
from typing import List, Dict, Any

# 服务器和节点的关联表
server_node_association = Table(
    'server_node_association',
    Base.metadata,
    Column('server_id', Integer, ForeignKey('opcua_servers.id', ondelete='CASCADE')),
    Column('node_id', Integer, ForeignKey('nodes.id', ondelete='CASCADE'))
)

class OPCUAServer(Base):
    """OPC UA服务器模型类"""
    __tablename__ = "opcua_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    endpoint = Column(String, nullable=True)  # 服务器监听地址，例如: opc.tcp://0.0.0.0:4840
    port = Column(Integer, nullable=False)     # 服务器监听端口
    status = Column(SQLEnum(ServerStatus), default=ServerStatus.STOPPED)
    last_started = Column(DateTime(timezone=True), nullable=True)
    uptime = Column(BigInteger, default=0)  # 运行时间（秒）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=False)
    
    # 与节点的多对多关系
    nodes = relationship(
        "Node",
        secondary=server_node_association,
        back_populates="servers",
        cascade="all, delete"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.status is None:
            self.status = ServerStatus.STOPPED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于序列化"""
        return {
            'id': self.id,
            'name': self.name,
            'endpoint': self.endpoint,
            'port': self.port,
            'status': self.status.value if isinstance(self.status, ServerStatus) else self.status,
            'last_started': self.last_started.isoformat() if self.last_started else None,
            'uptime': self.uptime,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'nodes': [node.to_dict() for node in self.nodes] if self.nodes else []
        }