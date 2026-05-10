# smart-cs-frontend/Dockerfile

# --- 阶段 1：构建阶段 ---
# 使用 Node 镜像来打包 Vue 项目
FROM node:18-alpine as build-stage

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
# 执行打包命令
RUN npm run build

# --- 阶段 2：运行阶段 ---
# 使用 Nginx 来托管静态文件
FROM nginx:stable-alpine as production-stage

# 删除默认的 Nginx 配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制自定义的 Nginx 配置文件（下一步创建）
COPY nginx.conf /etc/nginx/conf.d

# 将构建阶段的 dist 文件夹复制到 Nginx 的 HTML 目录
COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]