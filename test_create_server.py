import requests
import json
import logging
import random
import string
import time
from enum import Enum
from typing import Optional, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

def generate_random_string(length=10):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def create_server(data: Dict[str, Any]) -> bool:
    """通用服务器创建函数"""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        logging.info(f"准备创建服务器: {data['name']}")
        logging.debug("请求数据:\n%s", json.dumps(data, indent=2, ensure_ascii=False))
        
        response = requests.post('http://127.0.0.1:8000/servers/', json=data, headers=headers)
        logging.info("请求已发送，状态码: %d", response.status_code)
        
        response_text = response.text
        logging.debug("原始响应内容:\n%s", response_text)
        
        if response.headers.get('content-type', '').startswith('application/json'):
            response_json = response.json()
            logging.info("响应内容:\n%s", json.dumps(response_json, indent=2, ensure_ascii=False))
            return response.status_code == 200
            
        return False
        
    except Exception as e:
        logging.error("创建服务器失败: %s", str(e))
        return False

def test_basic_server():
    """测试创建基本服务器"""
    random_suffix = generate_random_string()
    data = {
        "name": f"test_server_{random_suffix}",
        "port": 4840,
        "endpoint": f"opc.tcp://0.0.0.0:4840/test_server_{random_suffix}",
        "nodeIds": []
    }
    return create_server(data)

def test_server_with_nodes():
    """测试创建带节点的服务器"""
    random_suffix = generate_random_string()
    data = {
        "name": f"test_server_with_nodes_{random_suffix}",
        "port": 4841,
        "endpoint": f"opc.tcp://0.0.0.0:4841/test_server_{random_suffix}",
        "nodeIds": [1, 2]  # 假设这些节点ID存在
    }
    return create_server(data)

def test_invalid_port_server():
    """测试无效端口范围"""
    random_suffix = generate_random_string()
    data = {
        "name": f"test_server_invalid_port_{random_suffix}",
        "port": 80,  # 小于1024的端口
        "endpoint": f"opc.tcp://0.0.0.0:80/test_server_{random_suffix}",
        "nodeIds": []
    }
    return not create_server(data)  # 期望失败

def test_duplicate_name():
    """测试重复名称"""
    name = f"test_server_{generate_random_string()}"
    data1 = {
        "name": name,
        "port": 4842,
        "endpoint": f"opc.tcp://0.0.0.0:4842/{name}",
        "nodeIds": []
    }
    
    # 创建第一个服务器
    success1 = create_server(data1)
    if not success1:
        return False
        
    # 尝试创建同名服务器
    data2 = {
        "name": name,
        "port": 4843,
        "endpoint": f"opc.tcp://0.0.0.0:4843/{name}",
        "nodeIds": []
    }
    return not create_server(data2)  # 期望失败

def test_duplicate_port():
    """测试重复端口"""
    port = random.randint(4844, 5000)
    data1 = {
        "name": f"test_server_{generate_random_string()}",
        "port": port,
        "endpoint": f"opc.tcp://0.0.0.0:{port}/server1",
        "nodeIds": []
    }
    
    # 创建第一个服务器
    success1 = create_server(data1)
    if not success1:
        return False
        
    # 尝试创建使用相同端口的服务器
    data2 = {
        "name": f"test_server_{generate_random_string()}",
        "port": port,
        "endpoint": f"opc.tcp://0.0.0.0:{port}/server2",
        "nodeIds": []
    }
    return not create_server(data2)  # 期望失败

if __name__ == "__main__":
    test_cases = [
        ("基本服务器创建", test_basic_server),
        ("带节点的服务器创建", test_server_with_nodes),
        ("无效端口测试", test_invalid_port_server),
        ("重复名称测试", test_duplicate_name),
        ("重复端口测试", test_duplicate_port)
    ]
    
    for test_name, test_func in test_cases:
        logging.info("=" * 50)
        logging.info(f"测试 {test_name}")
        logging.info("=" * 50)
        result = test_func()
        logging.info(f"测试结果: {'成功' if result else '失败'}")
        logging.info("")
        time.sleep(1)  # 添加延迟以便于观察输出 