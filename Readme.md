# MultiOpcS - 多服务器 OPC UA 管理系统

MultiOpcS 是一个用于管理多个 OPC UA 服务器的系统，提供了直观的 Web 界面来管理节点、服务器和数据。

## 功能特点

- 多服务器管理：支持创建和管理多个 OPC UA 服务器
- 节点管理：
  - 创建、编辑、删除节点
  - 批量创建节点（支持占位符）
  - 批量删除节点
- 服务器管理：
  - 创建、编辑、删除服务器
  - 启动/停止/重启服务器
  - 服务器状态实时监控
- 数据类型支持：
  - 数值类型：BOOL、CHAR、INT32、INT64、UINT16、UINT32、UINT64、FLOAT、DOUBLE
  - 字符串类型：STRING、DATETIME、BYTESTRING
- 实时状态更新：通过 WebSocket 实时更新服务器状态

## 技术栈

### 后端
- Python
- FastAPI
- asyncua (Python OPC UA)
- SQLAlchemy
- WebSocket

### 前端
- Next.js 14
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Tanstack Table

## 安装

### 后端

1. 创建虚拟环境：
```bash
python -m venv env
source env/bin/activate  # Linux/Mac
env\\Scripts\\activate   # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 启动后端服务：
```bash
uvicorn app.main:app --reload
```

### 前端

1. 安装依赖：
```bash
cd opcua-manager
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

## 使用说明

### 节点管理

1. 创建节点：
   - 单个创建：填写节点信息后点击创建
   - 批量创建：使用占位符 {n}，如 "sensor{n}" 创建 sensor1, sensor2, sensor3...

2. 编辑节点：
   - 修改节点名称、ID、数据类型等信息
   - 关联或取消关联服务器

3. 删除节点：
   - 单个删除：通过节点操作菜单
   - 批量删除：勾选多个节点后点击"删除所选"

### 服务器管理

1. 创建服务器：
   - 设置服务器名称、端口
   - 选择要发布的节点

2. 服务器操作：
   - 启动/停止/重启服务器
   - 编辑服务器配置
   - 查看服务器状态

## 开发说明

### 目录结构

```
.
├── app/                    # 后端代码
│   ├── api/               # API 路由
│   ├── core/              # 核心功能
│   ├── db/                # 数据库模型和操作
│   └── opcua/             # OPC UA 相关功能
│
└── opcua-manager/         # 前端代码
    ├── src/
    │   ├── app/          # Next.js 页面和组件
    │   ├── components/   # 通用组件
    │   ├── lib/         # 工具函数和 API 客户端
    │   └── types/       # TypeScript 类型定义
    └── public/          # 静态资源
```

## 许可证

MIT License

