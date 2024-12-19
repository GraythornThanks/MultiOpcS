from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from typing import Set, Dict
from datetime import datetime
import asyncio
from ..database import get_db
from .. import models
import logging
from contextlib import asynccontextmanager

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量
MAX_CONNECTIONS = 100
PING_INTERVAL = 15  # 减少到15秒
PING_TIMEOUT = 20   # 减少到20秒
active_connections: Set[WebSocket] = set()
ping_times: Dict[WebSocket, float] = {}

# 全局ping检查任务
ping_check_task = None

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
    
    logger.info(f"广播服务器状态: server_id={server_id}, status={status}")
    
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
            logger.debug(f"状态更新已发送到客户端")
        except Exception as e:
            logger.error(f"发送状态更新时出错: {e}")
            disconnected.add(connection)
    
    # 清理断开的连接
    for connection in disconnected:
        await cleanup_connection(connection)

async def cleanup_connection(websocket: WebSocket):
    """清理断开的连接"""
    try:
        if websocket in active_connections:
            active_connections.remove(websocket)
            logger.info(f"WebSocket连接已清理, 当前活动连接数: {len(active_connections)}")
        if websocket in ping_times:
            del ping_times[websocket]
        try:
            await websocket.close()
        except Exception:
            pass  # 忽略关闭时的错误
    except Exception as e:
        logger.error(f"清理连接时出错: {e}")

async def handle_ping(websocket: WebSocket):
    """处理ping消息"""
    try:
        current_time = asyncio.get_event_loop().time()
        ping_times[websocket] = current_time
        await websocket.send_text("pong")
        logger.debug(f"Pong已发送, 更新ping时间: {current_time}")
    except Exception as e:
        logger.error(f"处理ping消息时出错: {e}")
        await cleanup_connection(websocket)

async def check_ping_timeout():
    """检查ping超时的连接"""
    while True:
        try:
            await asyncio.sleep(PING_INTERVAL / 2)  # 更频繁地检查
            current_time = asyncio.get_event_loop().time()
            disconnected = set()
            
            for ws, last_ping in ping_times.items():
                if current_time - last_ping > PING_TIMEOUT:
                    logger.warning(f"WebSocket连接超时 (最后ping时间: {last_ping}, 当前时间: {current_time})")
                    disconnected.add(ws)
            
            for ws in disconnected:
                await cleanup_connection(ws)
                
            logger.debug(f"Ping检查完成, 当前活动连接数: {len(active_connections)}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"检查ping超时时出错: {e}")
            await asyncio.sleep(5)  # 错误后等待一段时间再继续

async def send_initial_status(websocket: WebSocket):
    """发送初始状态"""
    try:
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
        logger.info("已发送初始状态")
    except Exception as e:
        logger.error(f"发送初始状态时出错: {e}")
        raise

async def start_ping_check():
    """启动ping检查任务"""
    global ping_check_task
    if ping_check_task is None or ping_check_task.done():
        ping_check_task = asyncio.create_task(check_ping_timeout())
        logger.info("Ping检查任务已启动")

@asynccontextmanager
async def managed_connection(websocket: WebSocket):
    """管理WebSocket连接的上下文管理器"""
    try:
        if len(active_connections) >= MAX_CONNECTIONS:
            logger.warning(f"达到最大连接数限制 ({MAX_CONNECTIONS})")
            await websocket.close(code=1008)  # Policy Violation
            return
        
        await websocket.accept()
        active_connections.add(websocket)
        ping_times[websocket] = asyncio.get_event_loop().time()
        logger.info(f"新的WebSocket连接已经接受, 当前活动连接数: {len(active_connections)}")
        
        # 确保ping检查任务在运行
        await start_ping_check()
        
        yield
    finally:
        await cleanup_connection(websocket)

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    async with managed_connection(websocket):
        try:
            # 发送初始状态
            await send_initial_status(websocket)
            
            while True:
                try:
                    message = await websocket.receive_text()
                    if message == "ping":
                        await handle_ping(websocket)
                    elif message == "get_initial_status":
                        await send_initial_status(websocket)
                except WebSocketDisconnect:
                    logger.info("WebSocket连接断开")
                    break
                except Exception as e:
                    logger.error(f"处理WebSocket消息时出错: {e}")
                    break
                
        except Exception as e:
            logger.error(f"WebSocket错误: {e}")
            if not isinstance(e, WebSocketDisconnect):
                await websocket.close(code=1011)  # Internal Error