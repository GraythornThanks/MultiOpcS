## 安装

### 后端

1. 创建虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate   # Windows
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

