# 阶段一：构建前端
FROM node:24-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# 阶段二：后端运行时
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /fe/dist ./frontend/dist
ENV FRONTEND_DIST=frontend/dist
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
