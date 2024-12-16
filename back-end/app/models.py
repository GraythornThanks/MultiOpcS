from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table, Enum, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import enum
import operator
import ast
from typing import Any, Optional

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

class SafeExpressionEvaluator:
    """安全的表达式计算器"""
    
    def __init__(self):
        # 允许的操作符
        self.operators = {
            ast.Add: operator.add,  # +
            ast.Sub: operator.sub,  # -
            ast.Mult: operator.mul, # *
            ast.Div: operator.truediv,  # /
            ast.Mod: operator.mod,  # %
            ast.Pow: operator.pow,  # **
        }
        
        # 允许的变量
        self.allowed_names = {
            'trigger_value': None,  # 触发值
            'current_value': None,  # 当前值
        }

    def eval_expr(self, expr: str, trigger_value: Any, current_value: Any) -> float:
        """
        计算表达式
        :param expr: 表达式字符串
        :param trigger_value: 触发值
        :param current_value: 当前值
        :return: 计算结果
        """
        try:
            # 转换输入值为浮点数
            self.allowed_names['trigger_value'] = float(trigger_value)
            self.allowed_names['current_value'] = float(current_value)
            
            # 解析并计算表达式
            tree = ast.parse(expr, mode='eval')
            result = self._eval(tree.body)
            return float(result)
        except Exception as e:
            raise ValueError(f"表达式计算错误: {str(e)}")

    def _eval(self, node):
        """递归计算AST节点"""
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Name):
            if node.id not in self.allowed_names:
                raise ValueError(f"不允许使用变量: {node.id}")
            return self.allowed_names[node.id]
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in self.operators:
                raise ValueError(f"不支持的操作符: {type(node.op).__name__}")
            left = self._eval(node.left)
            right = self._eval(node.right)
            return self.operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -self._eval(node.operand)
            elif isinstance(node.op, ast.UAdd):
                return self._eval(node.operand)
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")

# 创建全局表达式计算器实例
expr_evaluator = SafeExpressionEvaluator()

def evaluate_conditional_change(value_change_config: dict, trigger_value: Any, current_value: Any) -> Optional[float]:
    """
    计算条件变化的新值
    :param value_change_config: 值变化配置
    :param trigger_value: 触发值
    :param current_value: 当前值
    :return: 计算后的新值，如果计算失败则返回 None
    """
    try:
        if not value_change_config:
            return None
            
        change_value = value_change_config.get('change_value', '')
        
        # 如果change_value包含表达式操作符，进行计算
        if any(op in change_value for op in '+-*/^()'):
            return expr_evaluator.eval_expr(change_value, trigger_value, current_value)
            
        # 如果不是表达式，尝试直接转换为浮点数
        return float(change_value)
        
    except Exception as e:
        print(f"[ERROR] 计算条件变化值时出错: {e}")
        return None

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

    def calculate_conditional_value(self, trigger_value: Any) -> Optional[float]:
        """
        计算条件变化的新值
        :param trigger_value: 触发值
        :return: 计算后的新值，如果计算失败则返回 None
        """
        try:
            if (self.value_change_type != ValueChangeType.CONDITIONAL or 
                not self.value_change_config):
                return None
                
            current_value = float(self.initial_value) if self.initial_value else 0.0
            return evaluate_conditional_change(
                self.value_change_config,
                trigger_value,
                current_value
            )
            
        except Exception as e:
            print(f"[ERROR] 节点条件变化值计算出错: {e}")
            return None