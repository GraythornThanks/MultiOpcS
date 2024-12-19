import requests
import json
import logging
import random
import string
import time
from enum import Enum
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

# 枚举定义
class DataType(str, Enum):
    BOOL = "BOOL"
    INT32 = "INT32"
    UINT32 = "UINT32"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    STRING = "STRING"
    DATETIME = "DATETIME"

class AccessLevel(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    READWRITE = "READWRITE"

class ValueChangeType(str, Enum):
    NONE = "NONE"
    LINEAR = "LINEAR"
    DISCRETE = "DISCRETE"
    RANDOM = "RANDOM"
    CONDITIONAL = "CONDITIONAL"

def generate_random_string(length=10):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def create_node(data):
    """通用节点创建函数"""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        logging.info(f"准备创建 {data['data_type']} 类型节点...")
        logging.debug("请求数据:\n%s", json.dumps(data, indent=2, ensure_ascii=False))
        
        response = requests.post('http://127.0.0.1:8000/nodes/', json=data, headers=headers)
        logging.info("请求已发送，状态码: %d", response.status_code)
        
        response_text = response.text
        logging.debug("原始响应内容:\n%s", response_text)
        
        if response.headers.get('content-type', '').startswith('application/json'):
            response_json = response.json()
            logging.info("响应内容:\n%s", json.dumps(response_json, indent=2, ensure_ascii=False))
            return response.status_code == 200
            
        return False
        
    except Exception as e:
        logging.error("创建节点失败: %s", str(e))
        return False

def test_bool_node():
    """测试布尔类型节点"""
    random_suffix = generate_random_string()
    data = {
        "name": f"bool_node_{random_suffix}",
        "node_id": f"ns=2;s=bool_node_{random_suffix}",
        "data_type": "BOOL",
        "access_level": "READWRITE",
        "description": "测试布尔类型节点",
        "initial_value": "true",
        "value_change_type": "DISCRETE",
        "value_change_config": {
            "values": ["true", "false"],
            "update_interval": 1000,
            "random_interval": True
        },
        "serverIds": []
    }
    return create_node(data)

def test_int32_node():
    """测试INT32类型节点"""
    random_suffix = generate_random_string()
    data = {
        "name": f"int32_node_{random_suffix}",
        "node_id": f"ns=2;s=int32_node_{random_suffix}",
        "data_type": "INT32",
        "access_level": "READWRITE",
        "description": "测试INT32类型节点",
        "initial_value": "100",
        "value_change_type": "RANDOM",
        "value_change_config": {
            "min_value": -1000,
            "max_value": 1000,
            "update_interval": 1000,
            "random_interval": True
        },
        "serverIds": []
    }
    return create_node(data)

def test_string_node():
    """测试字符串类型节点"""
    random_suffix = generate_random_string()
    data = {
        "name": f"string_node_{random_suffix}",
        "node_id": f"ns=2;s=string_node_{random_suffix}",
        "data_type": "STRING",
        "access_level": "READWRITE",
        "description": "测试字符串类型节点",
        "initial_value": "Hello, World!",
        "value_change_type": "DISCRETE",
        "value_change_config": {
            "values": ["Hello", "World", "OpenOPC", "Test"],
            "update_interval": 2000,
            "random_interval": False
        },
        "serverIds": []
    }
    return create_node(data)

def test_datetime_node():
    """测试日期时间类型节点"""
    random_suffix = generate_random_string()
    # 使用毫秒级精度的ISO 8601格式
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    data = {
        "name": f"datetime_node_{random_suffix}",
        "node_id": f"ns=2;s=datetime_node_{random_suffix}",
        "data_type": "DATETIME",
        "access_level": "READWRITE",
        "description": "测试日期时间类型节点",
        "initial_value": current_time,
        "value_change_type": "NONE",
        "serverIds": []
    }
    return create_node(data)

def test_conditional_node():
    """测试条件变化类型节点"""
    random_suffix = generate_random_string()
    data = {
        "name": f"conditional_node_{random_suffix}",
        "node_id": f"ns=2;s=conditional_node_{random_suffix}",
        "data_type": "DOUBLE",
        "access_level": "READWRITE",
        "description": "测试条件变化节点",
        "initial_value": "50.0",
        "value_change_type": "CONDITIONAL",
        "value_change_config": {
            "trigger_node_id": "ns=2;s=trigger_node",
            "trigger_value": "100",
            "change_value": "trigger_value * 2 + current_value"
        },
        "value_precision": 2,
        "serverIds": []
    }
    return create_node(data)

if __name__ == "__main__":
    test_cases = [
        ("布尔类型节点", test_bool_node),
        ("INT32类型节点", test_int32_node),
        ("字符串类型节点", test_string_node),
        ("日期时间类型节点", test_datetime_node),
        ("条件变化类型节点", test_conditional_node)
    ]
    
    for test_name, test_func in test_cases:
        logging.info("=" * 50)
        logging.info(f"测试 {test_name}")
        logging.info("=" * 50)
        result = test_func()
        logging.info(f"测试结果: {'成功' if result else '失败'}")
        logging.info("")
        time.sleep(1)  # 添加延迟以便于观察输出
 