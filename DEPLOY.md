# 🚀 部署上线指南

把演唱会票务监控系统部署到公网，让任何人都能访问。

---

## 第一步：部署后端到 Render（免费）

1. 打开 **[render.com](https://render.com)**，用 GitHub 账号注册/登录
2. 点击右上角 **「New +」→「Blueprint」**
3. 连接 GitHub 仓库 → 选择 `luoming-lot/concert-ticket-monitor`
4. Render 会自动读取 `render.yaml`，点击 **「Apply」**
5. 等待 3-5 分钟部署完成
6. 记下后端地址，类似：`https://concert-ticket-backend.onrender.com`

> ⚠️ Render 免费版 15 分钟无访问会自动休眠，再次访问需等待 30-60 秒唤醒。

---

## 第二步：部署前端到 Vercel（免费）

1. 打开 **[vercel.com](https://vercel.com)**，用 GitHub 账号注册/登录
2. 点击 **「New Project」**
3. 导入 `luoming-lot/concert-ticket-monitor`
4. 配置以下设置：
   - **Root Directory**：点击 `Edit`，选择 `frontend`
   - **Environment Variables**：添加一项
     - `VITE_API_URL` = `https://concert-ticket-backend.onrender.com`（换成你的 Render 地址）
5. 点击 **「Deploy」**
6. 等待 1-2 分钟，Vercel 会给你一个地址，如 `https://concert-ticket-monitor.vercel.app`

---

## 第三步：更新后端 CORS（如果报跨域错误）

如果前端访问后端报 CORS 跨域错误，在 Render 上添加环境变量：

1. Render Dashboard → 点击 `concert-ticket-backend` 服务
2. 左侧 **「Environment」**→ 添加：
   - `EXTRA_CORS_ORIGINS` = `https://你的前端地址.vercel.app`

或者直接改 [backend/app/main.py](backend/app/main.py) 里的 CORS 配置，加上 Vercel 域名后 push。

---

## 第四步：登录使用

1. 打开 Vercel 给你的前端地址
2. 默认账号：`admin` / `admin123`
3. 添加要监控的演出 URL → 开始监控

---

## 免费额度

| 平台 | 免费额度 | 限制 |
|------|---------|------|
| Render | 512MB RAM, 1GB 硬盘 | 15 分钟无访问自动休眠 |
| Vercel | 100GB 带宽/月 | 无限静态部署 |
