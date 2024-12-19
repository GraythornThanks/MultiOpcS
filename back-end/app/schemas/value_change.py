from pydantic import BaseModel
from typing import List

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