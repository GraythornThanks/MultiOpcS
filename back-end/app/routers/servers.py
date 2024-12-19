from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from ..database import get_db
from .. import models
from ..schemas import server as server_schema
from ..models.enums import ServerStatus
from asyncua import Server, ua
import asyncio
from .websocket import broadcast_server_status

router = APIRouter(
    prefix="/servers",
    tags=["servers"],
    responses={404: {"description": "Not found"}},
)

# 全局变量
active_servers = {}
active_connections = set()

async def update_server_status(server_id: int, status: ServerStatus, db: Session, last_started: datetime = None):
    """更新服务器状态并广播更新"""
    server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if server:
        server.status = status
        if last_started is not None:
            server.last_started = last_started
        db.commit()
        # 广播状态更新
        await broadcast_server_status(server_id, status.value, last_started)

@router.get("/", response_model=List[server_schema.OPCUAServer])
def get_servers(db: Session = Depends(get_db)):
    """获取所有服务器列表"""
    return db.query(models.OPCUAServer).all()

@router.get("/{server_id}", response_model=server_schema.OPCUAServerInfo)
def get_server(server_id: int, db: Session = Depends(get_db)):
    """获取单个服务器详情"""
    try:
        server = (
            db.query(models.OPCUAServer)
            .options(
                joinedload(models.OPCUAServer.nodes).load_only(
                    models.Node.id,
                    models.Node.name,
                    models.Node.node_id
                )
            )
            .filter(models.OPCUAServer.id == server_id)
            .first()
        )
        
        if server is None:
            raise HTTPException(
                status_code=404,
                detail=f"找不到ID为 {server_id} 的服务器"
            )
            
        return server
    except Exception as e:
        print(f"获取服务器详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取服务器详情失败: {str(e)}"
        )

@router.post("/", response_model=server_schema.OPCUAServer)
def create_server(server: server_schema.OPCUAServerCreate, db: Session = Depends(get_db)):
    """创建新服务器"""
    server_data = server.model_dump(exclude={"nodeIds"})
    db_server = models.OPCUAServer(**server_data)
    
    if server.nodeIds:
        nodes = db.query(models.Node).filter(models.Node.id.in_(server.nodeIds)).all()
        db_server.nodes = nodes
    
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

@router.put("/{server_id}", response_model=server_schema.OPCUAServer)
def update_server(server_id: int, server: server_schema.OPCUAServerUpdate, db: Session = Depends(get_db)):
    """更新服务器信息"""
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

@router.delete("/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db)):
    """删除服务器"""
    db_server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    db.delete(db_server)
    db.commit()
    return {"ok": True}

@router.post("/{server_id}/start")
async def start_server(server_id: int, db: Session = Depends(get_db)):
    """启动 OPC UA 服务器"""
    server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        print(f"\n[INFO] 正在启动服务器 '{server.name}' (ID: {server.id})...")
        
        # 更新服务器状态为启动中并广播
        start_time = datetime.now()
        await update_server_status(server_id, models.ServerStatus.STARTING, db, start_time)

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
                # 根据数据类型创建变量
                if node.data_type == models.DataType.BOOL:
                    var = await objects.add_variable(idx, node.name, False, ua.VariantType.Boolean)
                elif node.data_type == models.DataType.INT32:
                    var = await objects.add_variable(idx, node.name, 0, ua.VariantType.Int32)
                elif node.data_type == models.DataType.UINT16:
                    var = await objects.add_variable(idx, node.name, 0, ua.VariantType.UInt16)
                elif node.data_type == models.DataType.UINT32:
                    var = await objects.add_variable(idx, node.name, 0, ua.VariantType.UInt32)
                elif node.data_type == models.DataType.UINT64:
                    var = await objects.add_variable(idx, node.name, 0, ua.VariantType.UInt64)
                elif node.data_type == models.DataType.INT64:
                    var = await objects.add_variable(idx, node.name, 0, ua.VariantType.Int64)
                elif node.data_type == models.DataType.FLOAT:
                    var = await objects.add_variable(idx, node.name, 0.0, ua.VariantType.Float)
                elif node.data_type == models.DataType.DOUBLE:
                    var = await objects.add_variable(idx, node.name, 0.0, ua.VariantType.Double)
                elif node.data_type == models.DataType.STRING:
                    var = await objects.add_variable(idx, node.name, "", ua.VariantType.String)
                elif node.data_type == models.DataType.DATETIME:
                    var = await objects.add_variable(idx, node.name, datetime.now(), ua.VariantType.DateTime)
                else:
                    print(f"[WARNING] 不支持的数据类型: {node.data_type.value}")
                    continue
                
                # 设置访问级别
                if node.access_level == models.AccessLevel.READ:
                    await var.set_writable(False)
                elif node.access_level == models.AccessLevel.WRITE:
                    await var.set_read_only(False)
                elif node.access_level == models.AccessLevel.READWRITE:
                    await var.set_writable(True)
                    
                print(f"[INFO] 添加节点: {node.name} (类型: {node.data_type.value}, 访问级别: {node.access_level.value})")
            except Exception as e:
                print(f"[WARNING] 设置节点 {node.name} 时出错: {e}")
                continue
        
        await opc_server.start()
        active_servers[server_id] = opc_server
        print(f"[INFO] 服务器 '{server.name}' 启动成功! (地址: opc.tcp://0.0.0.0:{server.port})")
        
        # 更新服务器状态为运行中并广播
        server.endpoint = endpoint
        db.commit()
        await update_server_status(server_id, models.ServerStatus.RUNNING, db, start_time)
        
        return {"status": "success", "message": "Server started", "endpoint": endpoint}
    except Exception as e:
        error_msg = f"启动服务器 '{server.name}' 失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        # 发生错误时更新状态并广播
        await update_server_status(server_id, models.ServerStatus.ERROR, db)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/{server_id}/stop")
async def stop_server(server_id: int, db: Session = Depends(get_db)):
    """停止 OPC UA 服务器"""
    server = db.query(models.OPCUAServer).filter(models.OPCUAServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    print(f"\n[INFO] 正在停止服务器 '{server.name}' (ID: {server.id}, 地址: {server.endpoint})")
    
    opc_server = active_servers.get(server_id)
    if not opc_server:
        print(f"[INFO] 服务器 '{server.name}' 已经处于停止状态")
        await update_server_status(server_id, models.ServerStatus.STOPPED, db)
        return {"status": "success", "message": "Server already stopped"}

    try:
        await opc_server.stop()
        active_servers.pop(server_id)
        print(f"[INFO] 服务器 '{server.name}' 停止成功! (地址: {server.endpoint})")
        
        await update_server_status(server_id, models.ServerStatus.STOPPED, db)
        
        return {"status": "success", "message": "Server stopped"}
    except Exception as e:
        error_msg = f"停止服务器 '{server.name}' 失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        await update_server_status(server_id, models.ServerStatus.ERROR, db)
        raise HTTPException(status_code=500, detail=error_msg) 