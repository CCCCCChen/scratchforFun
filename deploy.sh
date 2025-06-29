#!/bin/bash

# 刮刮卡应用Docker部署脚本

set -e

echo "=== 刮刮卡应用部署脚本 ==="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "错误: docker-compose未安装，请先安装docker-compose"
    exit 1
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p data
mkdir -p ssl

# 停止现有容器（如果存在）
echo "停止现有容器..."
docker-compose down 2>/dev/null || true

# 构建镜像
echo "构建Docker镜像..."
docker-compose build

# 启动服务
echo "启动服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker-compose ps

# 显示访问信息
echo ""
echo "=== 部署完成 ==="
echo "应用已启动，可通过以下地址访问："
echo "HTTP: http://localhost:5000"
echo "如果配置了nginx: http://localhost"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo "重启服务: docker-compose restart"
echo ""

# 显示容器状态
echo "当前容器状态："
docker-compose ps