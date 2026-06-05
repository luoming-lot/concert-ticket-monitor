# ============================================
# 前端 Dockerfile - 多阶段构建
# ============================================

# --- 构建阶段 ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./

RUN npm install --registry=https://registry.npmmirror.com

COPY . .

RUN npm run build

# --- 生产阶段 ---
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
