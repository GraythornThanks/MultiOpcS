from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from .enums import DataType, AccessLevel, ValueChangeType
from .server import server_node_association
import operator
import ast
from typing import Any, Optional, Dict

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

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于序列化"""
        return {
            'id': self.id,
            'name': self.name,
            'node_id': self.node_id,
            'data_type': self.data_type.value if self.data_type else None,
            'access_level': self.access_level.value if self.access_level else None,
            'description': self.description,
            'initial_value': self.initial_value,
            'value_change_type': self.value_change_type.value if self.value_change_type else None,
            'value_change_config': self.value_change_config,
            'value_precision': self.value_precision,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'servers': [{'id': server.id, 'name': server.name} for server in self.servers] if self.servers else []
        } 