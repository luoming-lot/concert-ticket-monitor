# 部署上线指南

把演唱会票务监控系统部署到公网。

## 第一步：部署后端到 Render（免费）

1. 打开 Render 一键部署链接（需登录 Render 并授权 GitHub 仓库）：
   `https://render.com/deploy?repo=https://github.com/luoming-lot/concert-ticket-monitor`
2. 或者：render.com → **New +** → **Blueprint** → 选择本仓库 → **Apply**
3. `render.yaml` 已配置为**纯免费方案**：
   - Web 服务使用 Free 实例（750 小时/月，闲置 15 分钟自动休眠）
   - 数据库使用 Render 免费 Postgres（数据持久化，30 天后过期，过期前重新创建即可续期）
   - 无需持久磁盘（付费功能），无需绑卡
4. 等待 3-5 分钟构建部署完成（构建时会安装 Playwright Chromium，耗时较长）
5. 在 Render Dashboard 的服务页复制**真实服务地址**，形如：
   `https://concert-ticket-backend-xxxx.onrender.com`
   > ⚠️ Render 生成的服务地址带随机后缀，不要假设它就是
   > `concert-ticket-backend.onrender.com`，请以 Dashboard 显示为准。
6. 验证：浏览器打开 `https://<你的后端地址>/api/health`，应返回
   `{"status":"ok","version":"1.0.0"}`

> 💡 如果 Render 仍提示需要支付信息：这是账号策略（新工作区可能要求
> 预留卡），可放心绑定，Free 实例不会产生费用；或换用已有账号/工作区重试。

## 第二步：让前端指向后端（GitHub Pages）

后端地址确认后，重新构建前端并把 API 指过去：

```bash
cd frontend
set VITE_API_URL=https://<你的后端地址>/api
npm run build
cd ..
rem 把 dist 内容覆盖到 docs/ 并提交推送
```

也可以直接改 `frontend/src/api/index.js` 里的默认值后构建。

## 第三步：登录使用

1. 打开 `https://luoming-lot.github.io/concert-ticket-monitor`
2. 默认账号：`admin` / `admin123`

## 注意事项

- Render 免费版 15 分钟无访问会自动休眠，再次访问需等待 30-60 秒唤醒；
  监控任务只在服务唤醒期间运行；免费 Postgres 数据库 30 天过期，需提前续期。
- CORS 已放行 `*.github.io` 与 `*.vercel.app`，前端地址变化无需改后端。
- 大麦网有反爬风控，抢票/监控请在本机（有 Chrome）运行体验更佳。
