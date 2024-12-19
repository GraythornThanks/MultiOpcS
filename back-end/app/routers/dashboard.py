from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..database import get_db
from ..models.server import OPCUAServer, ServerStatus
from ..models.node import Node
import logging
import psutil
import platform

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)

def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": {
                "total": memory.total,
                "used": memory.used,
                "free": memory.available,
                "percent": memory.percent
            },
            "disk_usage": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        return {}

@router.get("/")
async def get_dashboard_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取仪表盘数据"""
    try:
        # 基础统计
        total_servers = db.query(OPCUAServer).count()
        total_nodes = db.query(Node).count()
        
        # 获取各数据类型节点数量
        node_types = db.query(Node.data_type, func.count(Node.id))\
            .group_by(Node.data_type)\
            .all()
        node_type_stats = {str(type_): count for type_, count in node_types}
        
        # 服务器状态统计
        server_status = db.query(OPCUAServer.status, func.count(OPCUAServer.id))\
            .group_by(OPCUAServer.status)\
            .all()
        server_status_stats = {str(status): count for status, count in server_status}
        
        # 获取最近更新的节点（前10个）
        recent_nodes = db.query(Node)\
            .order_by(desc(Node.updated_at))\
            .limit(10)\
            .all()
        
        # 获取最近更新的服务器（前10个）
        recent_servers = db.query(OPCUAServer)\
            .order_by(desc(OPCUAServer.updated_at))\
            .limit(10)\
            .all()
            
        # 获取系统信息
        system_info = get_system_info()
        
        # 计算服务器统计信息
        server_stats = db.query(
            func.count(OPCUAServer.id).label('total'),
            func.sum(case([(OPCUAServer.status == ServerStatus.RUNNING, 1)], else_=0)).label('running'),
            func.sum(case([(OPCUAServer.status == ServerStatus.STOPPED, 1)], else_=0)).label('stopped'),
            func.sum(case([(OPCUAServer.status == ServerStatus.ERROR, 1)], else_=0)).label('error'),
            func.avg(OPCUAServer.uptime).label('avg_uptime')
        ).first()
        
        # 计算节点统计信息
        node_stats = {
            "total": total_nodes,
            "by_type": node_type_stats,
            "by_access": db.query(Node.access_level, func.count(Node.id))\
                .group_by(Node.access_level)\
                .all()
        }
        
        # 计算平均在线时间
        avg_uptime = server_stats.avg_uptime or 0
        uptime_hours = round(avg_uptime / 3600, 2) if avg_uptime else 0
        
        return {
            # 基础统计
            "servers": {
                "total": total_servers,
                "running": server_stats.running or 0,
                "stopped": server_stats.stopped or 0,
                "error": server_stats.error or 0,
                "avg_uptime_hours": uptime_hours
            },
            "nodes": node_stats,
            
            # 系统状态
            "system_info": system_info,
            
            # 最近活动
            "recent_activities": {
                "nodes": [
                    {
                        "id": node.id,
                        "name": node.name,
                        "type": str(node.data_type),
                        "updated_at": node.updated_at.isoformat() if node.updated_at else None
                    } for node in recent_nodes
                ],
                "servers": [
                    {
                        "id": server.id,
                        "name": server.name,
                        "status": server.status.value if isinstance(server.status, ServerStatus) else str(server.status),
                        "uptime": server.uptime,
                        "updated_at": server.updated_at.isoformat() if server.updated_at else None
                    } for server in recent_servers
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"获取仪表盘数据时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取仪表盘数据失败: {str(e)}"
        )

@router.get("/performance")
async def get_performance_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取性能指标"""
    try:
        # 获取系统性能数据
        system_info = get_system_info()
        
        # 获取数据库性能指标
        db_stats = {
            "total_queries": db.query(func.count()).scalar(),
            "active_connections": db.execute("PRAGMA database_list;").fetchall().__len__(),
            "tables": {
                "servers": db.query(OPCUAServer).count(),
                "nodes": db.query(Node).count()
            }
        }
        
        # 获取服务器性能统计
        server_perf = db.query(
            func.avg(OPCUAServer.uptime).label('avg_uptime'),
            func.max(OPCUAServer.uptime).label('max_uptime'),
            func.min(case([(OPCUAServer.status == ServerStatus.RUNNING, OPCUAServer.uptime)], else_=None)).label('min_uptime')
        ).first()
        
        return {
            "system": system_info,
            "database": db_stats,
            "servers": {
                "avg_uptime": round(server_perf.avg_uptime or 0, 2),
                "max_uptime": server_perf.max_uptime or 0,
                "min_uptime": server_perf.min_uptime or 0
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取性能指标时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取性能指标失败: {str(e)}"
        )

@router.get("/alerts")
async def get_system_alerts(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """获取系统告警信息"""
    try:
        alerts = []
        
        # 检查服务器状态
        problem_servers = db.query(OPCUAServer)\
            .filter(OPCUAServer.status.in_([ServerStatus.STOPPED, ServerStatus.ERROR]))\
            .all()
        
        for server in problem_servers:
            severity = 'error' if server.status == ServerStatus.ERROR else 'warning'
            alerts.append({
                "type": f"server_{server.status.value}",
                "severity": severity,
                "message": f"服务器 {server.name} 当前状态: {server.status.value}",
                "timestamp": datetime.now().isoformat(),
                "server_id": server.id
            })
        
        # 检查系统资源
        system_info = get_system_info()
        
        # CPU告警
        cpu_usage = system_info.get("cpu_usage", 0)
        if cpu_usage > 90:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "error",
                "message": f"CPU使用率严重过高: {cpu_usage}%",
                "timestamp": datetime.now().isoformat()
            })
        elif cpu_usage > 80:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "message": f"CPU使用率过高: {cpu_usage}%",
                "timestamp": datetime.now().isoformat()
            })
            
        # 内存告警
        memory_percent = system_info.get("memory_usage", {}).get("percent", 0)
        if memory_percent > 90:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "error",
                "message": f"内存使用率严重过高: {memory_percent}%",
                "timestamp": datetime.now().isoformat()
            })
        elif memory_percent > 80:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "message": f"内存使用率过高: {memory_percent}%",
                "timestamp": datetime.now().isoformat()
            })
            
        # 磁盘告警
        disk_percent = system_info.get("disk_usage", {}).get("percent", 0)
        if disk_percent > 90:
            alerts.append({
                "type": "high_disk_usage",
                "severity": "error",
                "message": f"磁盘使用率严重过高: {disk_percent}%",
                "timestamp": datetime.now().isoformat()
            })
        elif disk_percent > 80:
            alerts.append({
                "type": "high_disk_usage",
                "severity": "warning",
                "message": f"磁盘使用率过高: {disk_percent}%",
                "timestamp": datetime.now().isoformat()
            })
            
        return alerts
        
    except Exception as e:
        logger.error(f"获取系统告警时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取系统告警失败: {str(e)}"
        ) 