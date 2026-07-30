# 🎫 演唱会票务监控系统

> 🌐 在线地址：[https://frontend-jade-psi-51.vercel.app](https://frontend-jade-psi-51.vercel.app)  
> 📦 GitHub：[luoming-lot/concert-ticket-monitor](https://github.com/luoming-lot/concert-ticket-monitor)

基于 FastAPI + Playwright + Vue3 的演唱会票务实时监控系统，支持多平台票务信息采集、库存/价格变化监控、多渠道通知推送。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.12 + FastAPI |
| 浏览器自动化 | Playwright |
| 数据库 | SQLite + SQLAlchemy |
| 前端框架 | Vue 3 + Element Plus + ECharts |
| 部署 | Docker + Docker Compose |

## 功能特性

- 🔍 **数据采集** — Playwright 自动化采集演出信息、场次、票档、库存状态
- 📊 **实时监控** — 定时检测票务状态变化（库存/价格/开售时间）
- 🔔 **多渠道通知** — 桌面通知、邮件、企业微信、钉钉机器人
- 🖥️ **Web 管理后台** — 仪表盘、演出管理、监控管理、系统配置
- 🐳 **一键部署** — Docker Compose 容器化部署

## 项目结构

```
concert-ticket-monitor/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库管理
│   │   ├── models/            # 数据模型
│   │   ├── routers/           # API 路由
│   │   ├── services/          # 业务服务
│   │   └── utils/             # 工具模块
│   ├── data/                  # 数据库文件
│   ├── logs/                  # 日志文件
│   ├── requirements.txt       # Python 依赖
│   └── Dockerfile
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── App.vue            # 根组件
│   │   ├── main.js            # 入口文件
│   │   ├── router/            # 路由配置
│   │   ├── views/             # 页面组件
│   │   ├── components/        # 通用组件
│   │   ├── api/               # API 接口
│   │   └── stores/            # 状态管理
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml          # 容器编排
├── .env                        # 环境变量
├── .env.example                # 环境变量示例
└── README.md
```

## 快速开始

### 方式一：本地开发

**环境要求：**
- Python 3.12+
- Node.js 20+
- 浏览器（Chrome/Chromium）

**1. 克隆项目**

```bash
git clone https://github.com/luoming-lot/concert-ticket-monitor.git
cd concert-ticket-monitor
```

**2. 配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，填写必要配置
```

**3. 启动后端**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**4. 启动前端**

```bash
cd frontend
npm install
npm run dev
```

**5. 访问系统**

- 🌐 前端：[frontend-jade-psi-51.vercel.app](https://frontend-jade-psi-51.vercel.app)
- 📄 API 文档：[backend-delta-six-95.vercel.app/docs](https://backend-delta-six-95.vercel.app/docs)
- 仓库：https://github.com/luoming-lot/concert-ticket-monitor
- 默认账号：admin / admin123

### 方式二：Docker 部署

```bash
# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/concerts | 获取演出列表 |
| POST | /api/concerts | 添加演出 |
| POST | /api/concerts/{id}/scrape | 采集数据 |
| GET | /api/monitor/status | 监控状态 |
| POST | /api/monitor/start | 启动监控 |
| POST | /api/monitor/stop/{id} | 停止监控 |
| GET | /api/settings | 获取配置 |
| PUT | /api/settings | 更新配置 |

## 许可证

MIT License
