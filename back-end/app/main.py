from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from contextlib import asynccontextmanager

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

# 全局变量
active_servers: Dict[int, Server] = {}
active_connections: Set[WebSocket] = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    print("[INFO] 正在启动应用...")
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 重置所有服务器状态为已停止
        servers = db.query(models.OPCUAServer).all()
        for server in servers:
            server.status = models.ServerStatus.STOPPED
            server.endpoint = None
        db.commit()
        print("[INFO] 已重置所有服务器状态为已停止")
        
    except Exception as e:
        print(f"[ERROR] 启动初始化时出错: {e}")
        if 'db' in locals():
            db.rollback()
    
    yield
    
    print("[INFO] 正在关闭应用...")
    try:
        if active_servers:
            # 获取数据库会话
            db = next(get_db())
            
            # 更新所有服务器状态
            servers = db.query(models.OPCUAServer).all()
            for server in servers:
                server.status = models.ServerStatus.STOPPED
                server.endpoint = None
            db.commit()
            
            # 清空活动服务器字典
            active_servers.clear()
            print("[INFO] 已强制关闭所有服务器")
    except Exception as e:
        print(f"[ERROR] 关闭时出错: {e}")
    finally:
        print("[INFO] 应用关闭完成")

# 创建 FastAPI 应用实例
app = FastAPI(
    title="OPCUA Manager",
    description="OPCUA Manager API 用于管理多个 OPCUA 服务器和节点。",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化工作"""
    print("[INFO] 应用启动...")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理工作"""
    print("[INFO] 正在执行应用关闭事件...")
    try:
        if active_servers:
            # 获取数据库会话
            db = next(get_db())
            
            # 更新所有服务器状态
            servers = db.query(models.OPCUAServer).all()
            for server in servers:
                server.status = models.ServerStatus.STOPPED
                server.endpoint = None
            db.commit()
            
            # 清空活动服务器字典
            active_servers.clear()
            print("[INFO] 已强制关闭所有服务器")
    except Exception as e:
        print(f"[ERROR] 关闭清理时出错: {e}")
    finally:
        print("[INFO] 应用关闭完成")

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
            float(value)  # 验证否为有效的浮点数
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
        # 如果称中没有占位符，使用节点ID中的范围
        start = int(node_id_match.group(1))
        end = int(node_id_match.group(2)) if node_id_match.group(2) else start
        
    for i in range(start, end + 1):
        expanded_name = re.sub(pattern, str(i), name)
        expanded_node_id = re.sub(pattern, str(i), node_id)
        results.append((expanded_name, expanded_node_id))
        
    return results

@app.post("/nodes/", response_model=schemas.Node)
def create_node(node: schemas.NodeCreate, db: Session = Depends(get_db)):
    try:
        # 验证节点ID格式
        if not validate_node_id(node.node_id):
            raise HTTPException(status_code=400, detail="节点ID格式无效")
        
        # 检查节点ID是否已存在
        existing_node = db.query(models.Node).filter(models.Node.node_id == node.node_id).first()
        if existing_node:
            raise HTTPException(status_code=400, detail="节点ID已存在")
        
        # 验证初始值
        if node.initial_value:
            is_valid, error_message = validate_initial_value(node.initial_value, node.data_type)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"初始值无效: {error_message}")
        
        # 验证��变化配置
        if node.value_change_type != models.ValueChangeType.NONE and not node.value_change_config:
            raise HTTPException(status_code=400, detail="值变化类型需要配置")
        
        # 验证数值精度
        if node.value_precision is not None:
            if node.data_type not in [models.DataType.FLOAT, models.DataType.DOUBLE]:
                raise HTTPException(status_code=400, detail="只有浮点数类型可以设置精度")
            if not (0 <= node.value_precision <= 10):
                raise HTTPException(status_code=400, detail="精度必须在0到10之间")
        
        # 创建新节点
        db_node = models.Node(
            name=node.name,
            node_id=node.node_id,
            data_type=node.data_type,
            access_level=node.access_level,
            description=node.description,
            initial_value=node.initial_value,
            value_change_type=node.value_change_type,
            value_change_config=node.value_change_config,
            value_precision=node.value_precision
        )
        
        # 如果指定了服务器ID，建立关联
        if node.serverIds:
            servers = db.query(models.OPCUAServer).filter(
                models.OPCUAServer.id.in_(node.serverIds)
            ).all()
            if len(servers) != len(node.serverIds):
                raise HTTPException(status_code=400, detail="一个或多个服务器ID不存在")
            db_node.servers = servers
        
        try:
            db.add(db_node)
            db.commit()
            db.refresh(db_node)
            return db_node
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"保存节点失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建节点失败: {str(e)}")

@app.put("/nodes/{node_id}", response_model=schemas.Node)
def update_node(node_id: int, node: schemas.NodeUpdate, db: Session = Depends(get_db)):
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # 如果更新节点ID，验证格式和唯一性
    if node.node_id is not None:
        if not validate_node_id(node.node_id):
            raise HTTPException(status_code=400, detail="Invalid node ID format")
        existing_node = db.query(models.Node).filter(
            models.Node.node_id == node.node_id,
            models.Node.id != node_id
        ).first()
        if existing_node:
            raise HTTPException(status_code=400, detail="Node ID already registered")
    
    # 更新节点属性
    update_data = node.dict(exclude_unset=True)
    
    # 果包含serverIds，更新服务器关联
    if "serverIds" in update_data:
        serverIds = update_data.pop("serverIds")
        if serverIds is not None:
            servers = db.query(models.OPCUAServer).filter(
                models.OPCUAServer.id.in_(serverIds)
            ).all()
            if len(servers) != len(serverIds):
                raise HTTPException(status_code=400, detail="One or more server IDs not found")
            db_node.servers = servers
    
    try:
        for key, value in update_data.items():
            setattr(db_node, key, value)
        db.commit()
        db.refresh(db_node)
        return db_node
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

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
            
            # 根据数据类型建变量
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
        # 发生错误更新状态
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