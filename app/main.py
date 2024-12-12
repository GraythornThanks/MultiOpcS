from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Set, Optional, Union, Tuple
from . import models, schemas
from .database import engine, get_db
import asyncio
from asyncua import Client, ua, Server
from datetime import datetime
import signal
import sys
import atexit
import json
import re
from sqlalchemy import or_

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OPCUA Manager",
    description="""
    OPCUA Manager API 用于管理多个 OPCUA 服务器和节点。
    
    主要功能:
    * 管理多个 OPCUA 服务器
    * 管理节点信息
    * 服务器和节点的关联管理
    """,
    version="1.0.0",
    contact={
        "name": "OPCUA Manager Team",
    },
    openapi_tags=[
        {
            "name": "nodes",
            "description": "节点管理操作，包括创建、读取、更新和删除节点",
        },
        {
            "name": "servers",
            "description": "OPCUA服务器管理操作，包括创建、读取、更新和删除服务器",
        },
        {
            "name": "associations",
            "description": "服务器和节点的关联管理",
        },
    ]
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 存储活动的 OPC UA 客户端连接
active_clients = {}

# 存储活动的 OPC UA 服务器实例
active_servers: Dict[int, Server] = {}

# 存储活动的 WebSocket 连接
active_connections: Set[WebSocket] = set()

async def cleanup_connections():
    """清理所有活动的 OPC UA 客户端连接"""
    for client in active_clients.values():
        if client:
            try:
                await client.disconnect()
            except Exception as e:
                print(f"断开连接时出错: {e}")
    active_clients.clear()

async def cleanup_servers():
    """清理所有活动的 OPC UA 服务器"""
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 停止所有活动的服务器
        for server_id, server in active_servers.items():
            try:
                await server.stop()
                db_server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
                if db_server:
                    db_server.status = models.ServerStatus.STOPPED
                    db_server.endpoint = None
            except Exception as e:
                print(f"停止服务器 {server_id} 时出错: {e}")
        
        # 更新数据库中所有服务器状态
        servers = db.query(models.OPCUAServer).all()
        for server in servers:
            server.status = models.ServerStatus.STOPPED
            server.endpoint = None
        
        db.commit()
        active_servers.clear()
        
    except Exception as e:
        print(f"清理服务器时出错: {e}")

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化工作"""
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 确保所有服务器状态为已停止
        servers = db.query(models.OPCUAServer).all()
        for server in servers:
            if server.status != models.ServerStatus.STOPPED:
                server.status = models.ServerStatus.STOPPED
                server.endpoint = None
        db.commit()
        
    except Exception as e:
        print(f"[ERROR] 启动初始化时出错: {e}")
        db.rollback()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理工作"""
    try:
        # 获取数据库会话
        db = next(get_db())
        # 停止所有活动的服务器
        for server_id, server in active_servers.items():
            try:
                await server.stop()
                db_server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
                if db_server:
                    db_server.status = models.ServerStatus.STOPPED
                    db_server.endpoint = None
            except Exception as e:
                print(f"停止服务器 {server_id} 时出错: {e}")
        
        # 更新数据库中所有服务器状态
        servers = db.query(models.OPCUAServer).all()
        for server in servers:
            server.status = models.ServerStatus.STOPPED
            server.endpoint = None
        
        db.commit()
        active_servers.clear()
        
        # 清理 WebSocket 连接
        for connection in active_connections.copy():
            try:
                await connection.close()
            except Exception:
                pass
        active_connections.clear()
        
    except Exception as e:
        print(f"关闭清理时出错: {e}")

def sync_cleanup():
    """同清理函数"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cleanup_connections())
        loop.run_until_complete(cleanup_servers())
        loop.close()
    except Exception as e:
        print(f"清理连接和服务器时出错: {e}")

# 注册同步清理函数
atexit.register(sync_cleanup)

def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    print("\n正在关闭所有 OPC UA 连接和服务器...")
    sync_cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def connect_server(server_id: int, endpoint: str, db: Session):
    """连接到 OPC UA 服务器"""
    try:
        client = Client(endpoint)
        await client.connect()
        active_clients[server_id] = client
        
        # 更新服务器状态
        server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
        if server:
            server.status = models.ServerStatus.RUNNING
            server.last_connected = datetime.now()
            db.commit()
        
        return True
    except Exception as e:
        print(f"连接服务器失败: {e}")
        server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
        if server:
            server.status = models.ServerStatus.ERROR
            db.commit()
        return False

async def disconnect_server(server_id: int, db: Session):
    """断开 OPC UA 服务器连接"""
    client = active_clients.get(server_id)
    if client:
        try:
            await client.disconnect()
            active_clients.pop(server_id)
            
            # 更新服务器状态
            server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
            if server:
                server.status = models.ServerStatus.STOPPED
                db.commit()
            return True
        except Exception as e:
            print(f"断开服务器连接失败: {e}")
            return False
    return False

# Node CRUD operations
@app.get("/nodes/", response_model=List[schemas.Node])
def get_nodes(db: Session = Depends(get_db)):
    return db.query(models.Node).all()

@app.get("/nodes/{node_id}", response_model=schemas.Node)
def get_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node

# 节点ID格式验证
def validate_node_id(node_id: str) -> bool:
    node_id_pattern = re.compile(r'^(ns=\d+;)?[isb]=.+$')
    return bool(node_id_pattern.match(node_id))

# 初始值验证
def validate_initial_value(value: Optional[str], data_type: models.DataType) -> tuple[bool, str]:
    if not value:
        return True, ""
        
    try:
        if data_type == models.DataType.BOOL:
            if value.lower() not in ['true', 'false']:
                return False, "布尔值必须是 true 或 false"
        elif data_type == models.DataType.CHAR:
            if len(value) != 1:
                return False, "字符类型必须是单个字符"
        elif data_type == models.DataType.INT32:
            val = int(value)
            if val < -2147483648 or val > 2147483647:
                return False, "INT32 的值必须在 -2147483648 到 2147483647 之间"
        elif data_type == models.DataType.INT64:
            val = int(value)
            if val < -9223372036854775808 or val > 9223372036854775807:
                return False, "INT64 的值超出范围"
        elif data_type == models.DataType.UINT16:
            val = int(value)
            if val < 0 or val > 65535:
                return False, "UINT16 的值必须在 0 到 65535 之间"
        elif data_type == models.DataType.UINT32:
            val = int(value)
            if val < 0 or val > 4294967295:
                return False, "UINT32 的值必须在 0 到 4294967295 之间"
        elif data_type == models.DataType.UINT64:
            val = int(value)
            if val < 0 or val > 18446744073709551615:
                return False, "UINT64 的值超出范围"
        elif data_type == models.DataType.FLOAT or data_type == models.DataType.DOUBLE:
            float(value)  # 验证��否为有效的浮点数
        elif data_type == models.DataType.DATETIME:
            # 验证ISO 8601格式
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$', value):
                return False, "日期时间必须符合 ISO 8601 格式 (YYYY-MM-DDThh:mm:ss.sssZ)"
            try:
                datetime.strptime(value.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                return False, "无效的日期时间"
        return True, ""
    except ValueError as e:
        return False, str(e)

def parse_node_pattern(name: str, node_id: str) -> List[Tuple[str, str]]:
    """解析节点名称和ID中的占位符模式，返回展开后的节点名称和ID列表"""
    # 查找模式 {n} 或 {start-end}
    pattern = r'\{(\d+)(?:-(\d+))?\}'
    name_match = re.search(pattern, name)
    node_id_match = re.search(pattern, node_id)
    
    if not name_match and not node_id_match:
        return [(name, node_id)]
        
    results = []
    
    if name_match:
        start = int(name_match.group(1))
        end = int(name_match.group(2)) if name_match.group(2) else start
    else:
        # 如果名称中没有占位符，使用节点ID中的范围
        start = int(node_id_match.group(1))
        end = int(node_id_match.group(2)) if node_id_match.group(2) else start
        
    for i in range(start, end + 1):
        expanded_name = re.sub(pattern, str(i), name)
        expanded_node_id = re.sub(pattern, str(i), node_id)
        results.append((expanded_name, expanded_node_id))
        
    return results

@app.post("/nodes/", response_model=List[schemas.Node])
def create_node(node: schemas.NodeCreate, db: Session = Depends(get_db)):
    """创建新节点，支持批量创建"""
    try:
        # 解析节点模式
        node_patterns = parse_node_pattern(node.name, node.node_id)
        created_nodes = []
        
        for name, node_id in node_patterns:
            # 1. 验证节点名称是否已存在
            existing_name = db.query(models.Node).filter(models.Node.name == name).first()
            if existing_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"节点名称 '{name}' 已存在"
                )

            # 2. 验证节点ID格式
            if not validate_node_id(node_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"节点ID '{node_id}' 格式无效"
                )

            # 3. 验证节点ID是否已存在
            existing_node_id = db.query(models.Node).filter(models.Node.node_id == node_id).first()
            if existing_node_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"节点ID '{node_id}' 已存在"
                )

            # 4. 验证初始值
            if node.initial_value:
                is_valid, error_message = validate_initial_value(node.initial_value, node.data_type)
                if not is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"初始值无效: {error_message}"
                    )

            # 5. 创建节点
            node_data = node.model_dump(exclude={"serverIds"})
            node_data["name"] = name
            node_data["node_id"] = node_id
            db_node = models.Node(**node_data)
            
            # 6. 处理服务器关联
            if hasattr(node, 'serverIds') and node.serverIds:
                servers = db.query(models.OPCUAServer).filter(models.OPCUAServer.id.in_(node.serverIds)).all()
                db_node.servers = servers
            
            db.add(db_node)
            created_nodes.append(db_node)
        
        db.commit()
        for node in created_nodes:
            db.refresh(node)
            
        return created_nodes
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建节点失败: {str(e)}"
        )

@app.put("/nodes/{node_id}", response_model=schemas.Node)
def update_node(node_id: int, node: schemas.NodeUpdate, db: Session = Depends(get_db)):
    """更新节点"""
    try:
        db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
        if db_node is None:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        print(f"\n[INFO] 更新节点: {db_node.name} (ID: {db_node.node_id})")
        
        # 如果要更新节点 ID，检查新的节点 ID 是否已存在
        if node.node_id and node.node_id != db_node.node_id:
            existing_node = db.query(models.Node).filter(models.Node.node_id == node.node_id).first()
            if existing_node:
                raise HTTPException(
                    status_code=400,
                    detail=f"节点 ID '{node.node_id}' 已存在"
                )
        
        update_data = node.model_dump(exclude_unset=True)
        server_ids = update_data.pop("serverIds", None)
        
        # 更新基本字段
        for key, value in update_data.items():
            print(f"[INFO] 更新字段 {key}: {value}")
            setattr(db_node, key, value)
        
        # 更新服务器关联
        if server_ids is not None:
            servers = db.query(models.OPCUAServer).filter(models.OPCUAServer.id.in_(server_ids)).all()
            db_node.servers = servers
            print(f"[INFO] 更新服务器关联: {server_ids}")
        
        db.commit()
        db.refresh(db_node)
        
        print(f"[INFO] 节点更新成功!")
        return db_node
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 更新节点失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新节点失败: {str(e)}"
        )

@app.delete("/nodes/{node_id}")
def delete_node(node_id: int, db: Session = Depends(get_db)):
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    
    db.delete(db_node)
    db.commit()
    return {"ok": True}

# OPCUAServer CRUD operations
@app.get("/servers/", response_model=List[schemas.OPCUAServer])
def get_servers(db: Session = Depends(get_db)):
    return db.query(models.OPCUAServer).all()

@app.get("/servers/{server_id}", response_model=schemas.OPCUAServer)
def get_server(server_id: int, db: Session = Depends(get_db)):
    server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@app.post("/servers/", response_model=schemas.OPCUAServer)
def create_server(server: schemas.OPCUAServerCreate, db: Session = Depends(get_db)):
    server_data = server.model_dump(exclude={"nodeIds"})
    db_server = models.OPCUAServer(**server_data)
    
    if server.nodeIds:
        nodes = db.query(models.Node).filter(models.Node.id.in_(server.nodeIds)).all()
        db_server.nodes = nodes
    
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

@app.put("/servers/{server_id}", response_model=schemas.OPCUAServer)
def update_server(server_id: int, server: schemas.OPCUAServerUpdate, db: Session = Depends(get_db)):
    db_server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    update_data = server.model_dump(exclude_unset=True)
    nodeIds = update_data.pop("nodeIds", None)
    
    for key, value in update_data.items():
        setattr(db_server, key, value)
    
    if nodeIds is not None:
        nodes = db.query(models.Node).filter(models.Node.id.in_(nodeIds)).all()
        db_server.nodes = nodes
    
    db.commit()
    db.refresh(db_server)
    return db_server

@app.delete("/servers/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db)):
    db_server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    db.delete(db_server)
    db.commit()
    return {"ok": True}

# Server-Node Association endpoints
@app.post("/servers/{server_id}/nodes/{node_id}", response_model=schemas.OPCUAServer, tags=["associations"])
def add_node_to_server(server_id: int, node_id: int, db: Session = Depends(get_db)):
    """
    将节点添加到服务器
    
    - **server_id**: 服务器ID
    - **node_id**: 节点ID
    """
    db_server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
        
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Node not found")
        
    db_server.nodes.append(db_node)
    db.commit()
    db.refresh(db_server)
    return db_server

@app.delete("/servers/{server_id}/nodes/{node_id}", response_model=schemas.OPCUAServer, tags=["associations"])
def remove_node_from_server(server_id: int, node_id: int, db: Session = Depends(get_db)):
    db_server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
        
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Node not found")
        
    db_server.nodes.remove(db_node)
    db.commit()
    db.refresh(db_server)
    return db_server

@app.get("/")
async def root():
    return {"message": "Welcome to OPCUA Manager"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

async def setup_server_nodes(server: Server, db_server: models.OPCUAServer):
    """设置服务器的节点"""
    # 创建一个对象用于组织节点
    objects = server.nodes.objects

    # 为每个节点创建变量
    for node in db_server.nodes:
        try:
            var_name = f"{node.name}_{node.id}"
            
            # 根据数据类型创建变量
            if node.data_type == "Boolean":
                var = await objects.add_variable(ua.NodeId(var_name), node.name, False)
            elif node.data_type == "Int32":
                var = await objects.add_variable(ua.NodeId(var_name), node.name, 0)
            elif node.data_type == "Float":
                var = await objects.add_variable(ua.NodeId(var_name), node.name, 0.0)
            elif node.data_type == "String":
                var = await objects.add_variable(ua.NodeId(var_name), node.name, "")
            elif node.data_type == "DateTime":
                var = await objects.add_variable(ua.NodeId(var_name), node.name, datetime.now())
            else:
                continue

            # 设置访问权限
            if node.access_level == "read":
                await var.set_writable(False)
            elif node.access_level == "write":
                await var.set_read_only(False)
            elif node.access_level == "read_write":
                await var.set_writable(True)

            # 设置描述
            if node.description:
                await var.set_description(node.description)

        except Exception as e:
            print(f"设置节点 {node.name} 时出错: {e}")

async def broadcast_server_status(server_id: int, status: str, last_started: datetime = None):
    """向所有连接的客户端广播服务器状态更新"""
    message = {
        "type": "server_status",
        "data": {
            "id": server_id,
            "status": status,
            "last_started": last_started.isoformat() if last_started else None
        }
    }
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            print(f"发送状态更新时出错: {e}")
            active_connections.remove(connection)

def convert_initial_value(data_type: str, value: str):
    """转换初始值为正确的数据类型"""
    if not value:
        return None
        
    try:
        if data_type == "BOOL":
            return value.lower() == 'true'
        elif data_type == "INT32":
            return int(value)
        elif data_type == "UINT16":
            val = int(value)
            if not (0 <= val <= 65535):
                raise ValueError("UINT16 must be between 0 and 65535")
            return val
        elif data_type == "UINT32":
            val = int(value)
            if not (0 <= val <= 4294967295):
                raise ValueError("UINT32 must be between 0 and 4294967295")
            return val
        elif data_type == "UINT64":
            val = int(value)
            if not (0 <= val <= 18446744073709551615):
                raise ValueError("UINT64 must be between 0 and 18446744073709551615")
            return val
        elif data_type == "INT64":
            val = int(value)
            if not (-9223372036854775808 <= val <= 9223372036854775807):
                raise ValueError("INT64 must be between -9223372036854775808 and 9223372036854775807")
            return val
        elif data_type == "FLOAT":
            return float(value)
        elif data_type == "DOUBLE":
            return float(value)
        elif data_type == "STRING":
            return str(value)
        elif data_type == "DATETIME":
            return datetime.strptime(value.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f')
        elif data_type == "BYTESTRING":
            return value.encode()
        else:
            return value
    except (ValueError, TypeError) as e:
        print(f"[WARNING] 转换值 '{value}' 为类型 {data_type} 失败: {str(e)}")
        return None  # 转换失败时返回 None

@app.post("/servers/{server_id}/start")
async def start_server(server_id: int, db: Session = Depends(get_db)):
    """启动 OPC UA 服务器"""
    server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        print(f"\n[INFO] 正在启动服务器 '{server.name}' (ID: {server.id})...")
        
        # 更新服务器状态为启动中
        server.status = models.ServerStatus.STARTING
        server.last_started = datetime.now()
        db.commit()
        await broadcast_server_status(server_id, server.status.value, server.last_started)

        # 创建并启动服务器
        opc_server = Server()
        await opc_server.init()
        
        endpoint = f"opc.tcp://0.0.0.0:{server.port}/freeopcua/server/"
        opc_server.set_endpoint(endpoint)
        print(f"[INFO] 设置服务器端点: {endpoint}")
        
        # 设置服务器名称
        uri = f"urn:{server.name}"
        opc_server.set_server_name(server.name)
        idx = await opc_server.register_namespace(uri)
        print(f"[INFO] 注册命名空间: {uri}")
        
        # 为服务器添加关联的节点
        objects = opc_server.nodes.objects
        for node in server.nodes:
            try:
                # 转换初始值为正确的数据类型
                initial_value = convert_initial_value(node.data_type.value, node.initial_value) if node.initial_value else None
                
                # 根据数据类型创建变量
                if node.data_type == models.DataType.BOOL:
                    var = await objects.add_variable(idx, node.name, initial_value or False, ua.VariantType.Boolean)
                elif node.data_type == models.DataType.INT32:
                    var = await objects.add_variable(idx, node.name, initial_value or 0, ua.VariantType.Int32)
                elif node.data_type == models.DataType.UINT16:
                    var = await objects.add_variable(idx, node.name, initial_value or 0, ua.VariantType.UInt16)
                elif node.data_type == models.DataType.UINT32:
                    var = await objects.add_variable(idx, node.name, initial_value or 0, ua.VariantType.UInt32)
                elif node.data_type == models.DataType.UINT64:
                    var = await objects.add_variable(idx, node.name, initial_value or 0, ua.VariantType.UInt64)
                elif node.data_type == models.DataType.INT64:
                    var = await objects.add_variable(idx, node.name, initial_value or 0, ua.VariantType.Int64)
                elif node.data_type == models.DataType.FLOAT:
                    var = await objects.add_variable(idx, node.name, initial_value or 0.0, ua.VariantType.Float)
                elif node.data_type == models.DataType.DOUBLE:
                    var = await objects.add_variable(idx, node.name, initial_value or 0.0, ua.VariantType.Double)
                elif node.data_type == models.DataType.STRING:
                    var = await objects.add_variable(idx, node.name, initial_value or "", ua.VariantType.String)
                elif node.data_type == models.DataType.DATETIME:
                    var = await objects.add_variable(idx, node.name, initial_value or datetime.now(), ua.VariantType.DateTime)
                else:
                    print(f"[WARNING] 不支持的数据类型: {node.data_type.value}")
                    continue
                
                # 设置访问级别
                if node.access_level.value == models.AccessLevel.READ.value:
                    await var.set_writable(False)
                elif node.access_level.value == models.AccessLevel.WRITE.value:
                    await var.set_read_only(False)
                elif node.access_level.value == models.AccessLevel.READWRITE.value:
                    await var.set_writable(True)
                    
                print(f"[INFO] 添加节点: {node.name} (类型: {node.data_type.value}, 访问级别: {node.access_level.value}, 初始值: {initial_value})")
            except Exception as e:
                print(f"[WARNING] 设置节点 {node.name} 时出错: {e}")
                continue
        
        await opc_server.start()
        active_servers[server_id] = opc_server
        print(f"[INFO] 服务器 '{server.name}' 启动成功! (地址: opc.tcp://0.0.0.0:{server.port})")
        
        # 更新服务器状态为运行中
        server.status = models.ServerStatus.RUNNING
        server.endpoint = endpoint
        db.commit()
        await broadcast_server_status(server_id, server.status.value, server.last_started)
        
        return {"status": "success", "message": "Server started", "endpoint": endpoint}
    except Exception as e:
        error_msg = f"启动服务器 '{server.name}' 失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        # 发生错误时更新状态
        server.status = models.ServerStatus.ERROR
        db.commit()
        await broadcast_server_status(server_id, server.status.value, server.last_started)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/servers/{server_id}/stop")
async def stop_server(server_id: int, db: Session = Depends(get_db)):
    """停止 OPC UA 服务器"""
    server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    print(f"\n[INFO] 正在停止服务器 '{server.name}' (ID: {server.id}, 地址: {server.endpoint})")
    
    opc_server = active_servers.get(server_id)
    if not opc_server:
        print(f"[INFO] 服务器 '{server.name}' 已经处于停止状态")
        server.status = models.ServerStatus.STOPPED
        db.commit()
        await broadcast_server_status(server_id, server.status.value, server.last_started)
        return {"status": "success", "message": "Server already stopped"}

    try:
        await opc_server.stop()
        active_servers.pop(server_id)
        print(f"[INFO] 服务器 '{server.name}' 停止成功! (地址: {server.endpoint})")
        
        server.status = models.ServerStatus.STOPPED
        db.commit()
        await broadcast_server_status(server_id, server.status.value, server.last_started)
        
        return {"status": "success", "message": "Server stopped"}
    except Exception as e:
        error_msg = f"停止服务器 '{server.name}' 失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        server.status = models.ServerStatus.ERROR
        db.commit()
        await broadcast_server_status(server_id, server.status.value, server.last_started)
        raise HTTPException(status_code=500, detail=error_msg)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        active_connections.add(websocket)
        
        # 发送初始状态
        db = next(get_db())
        servers = db.query(models.OPCUAServer).all()
        initial_status = [{
            "id": server.id,
            "status": server.status.value,
            "last_started": server.last_started.isoformat() if server.last_started else None
        } for server in servers]
        
        await websocket.send_json({
            "type": "initial_status",
            "data": initial_status
        })
        
        try:
            while True:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_text("pong")
                    continue
                
                # 处理其他类型的消息...
                
        except WebSocketDisconnect:
            active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表盘统计数据"""
    # 获取服务器总数
    total_servers = db.query(models.OPCUAServer).count()
    
    # 获取运行中的服务器数量
    running_servers = db.query(models.OPCUAServer).filter(
        models.OPCUAServer.status == models.ServerStatus.RUNNING
    ).count()
    
    # 获取节点总数
    total_nodes = db.query(models.Node).count()
    
    return {
        "total_servers": total_servers,
        "running_servers": running_servers,
        "total_nodes": total_nodes,
    } 