from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Set, Optional, Union, Tuple
from . import models
from . import schemas
from .models.base import Base
from .models.node import Node
from .models.server import OPCUAServer
from .models.enums import ServerStatus, DataType, AccessLevel, ValueChangeType
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
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from .routers import servers, nodes, websocket

# 创建数据库表
Base.metadata.create_all(bind=engine)

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
            server.status = ServerStatus.STOPPED
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
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 包含路由
app.include_router(servers.router)
app.include_router(nodes.router)
app.include_router(websocket.router)

@app.get("/")
async def root():
    return {"message": "Welcome to OPCUA Manager"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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