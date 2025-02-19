## 安装

### 后端

1. 创建虚拟环境：
```bash
cd back-end
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate   # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
pip install 'uvicorn[standard]' # uvicorn 另外安装标准版
```

3. 启动后端服务：
```bash
uvicorn app.main:app --reload
```

### 前端

1. 安装依赖：
```bash
cd front-end
npm install -g pnpm 
# 推荐使用pnpm
pnpm install
```

2. 启动开发服务器：
```bash
pnpm dev
```

