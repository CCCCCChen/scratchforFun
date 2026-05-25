# 刮刮卡应用 Docker 部署指南

## 快速开始

### 1. 本地部署

```bash
# 克隆项目（如果还没有）
git clone <your-repo-url>
cd scratchforFun

# 使用docker-compose部署
docker-compose up -d

# 或使用部署脚本
chmod +x deploy.sh
./deploy.sh
```

访问 http://localhost:5000（如果配置了子路径，访问 http://localhost/scratch4fun/）

### 2. 生产环境部署

#### 准备工作

1. **服务器要求**
   - Ubuntu 18.04+ / CentOS 7+ / Debian 9+
   - 至少 1GB RAM
   - 至少 10GB 磁盘空间
   - Docker 和 docker-compose

2. **安装 Docker**

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 部署步骤

1. **上传代码到服务器**

```bash
# 方法1: 使用git
git clone <your-repo-url>
cd scratchforFun

# 方法2: 使用scp上传
scp -r ./scratchforFun user@your-server:/path/to/app
```

2. **配置环境**

```bash
# 修改nginx配置中的域名
vim nginx.conf
# 将 your-domain.com 替换为你的实际域名

# 如果需要HTTPS，准备SSL证书
mkdir ssl
# 将证书文件放入ssl目录
# cert.pem (证书文件)
# key.pem (私钥文件)
```

3. **启动应用**

```bash
# 使用部署脚本
chmod +x deploy.sh
./deploy.sh

# 或手动启动
mkdir -p data
docker compose up -d scratch-app
```

4. **配置防火墙**

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

## 配置说明

### 环境变量

在 `docker-compose.yml` 中可以配置以下环境变量：

```yaml
environment:
  - FLASK_ENV=production
  - SECRET_KEY=your-secret-key  # 建议设置随机密钥
  - URL_PREFIX=/scratch4fun
  - ADMIN_INIT_PASSWORD=change-me
  - DATABASE_FILE=/app/data/xx.sqlite
  - SETTINGS_FILE=/app/data/setting.json
```

### 数据持久化

应用数据存储在以下位置：
- 数据库文件: `./data/xx.sqlite`
- 配置文件: `./data/setting.json`

## 与现有 Nginx（80/443 已占用）共存

如果云服务器上已经有一个 Nginx（例如你提供的 `warehouse.hchch.tech` 配置）占用了 80/443，那么不要再启动本项目的 `nginx` 容器（否则端口冲突）。

建议做法：
1. 只启动 `scratch-app`（暴露一个宿主机端口，比如 5000 或 5005）。
2. 在“现有”的 Nginx 配置里新增一个 `location /scratch4fun/` 反代到该端口。
3. 为目标域名申请证书（如果不是沿用现有证书的域名）。

### 方式 A：挂在同一个域名下（推荐最省事）

如果你允许用已有的域名（例如 `warehouse.hchch.tech`）来访问刮刮卡，那么直接在对应的 `server { server_name warehouse.hchch.tech; ... }` 里加：

```nginx
location = /scratch4fun {
  return 301 /scratch4fun/;
}

location /scratch4fun/ {
  proxy_pass http://127.0.0.1:5000;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_connect_timeout 60s;
  proxy_send_timeout 60s;
  proxy_read_timeout 60s;
}
```

访问：`https://warehouse.hchch.tech/scratch4fun/`

### 方式 B：使用另一个域名（例如 hchch.tech）

这种方式需要为 `hchch.tech` 单独申请证书，然后新增两个 server block（80/443）。示例：

```nginx
server {
  listen 80;
  server_name hchch.tech;

  location /.well-known/acme-challenge/ {
    root /var/www/certbot;
  }

  location / {
    return 301 https://$host$request_uri;
  }
}

server {
  listen 443 ssl;
  http2 on;
  server_name hchch.tech;

  ssl_certificate     /etc/letsencrypt/live/hchch.tech/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/hchch.tech/privkey.pem;

  location = /scratch4fun {
    return 301 /scratch4fun/;
  }

  location /scratch4fun/ {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
  }
}
```

访问：`https://hchch.tech/scratch4fun/`

### 应用侧必须配置 URL_PREFIX

子路径访问必须保持：
- `URL_PREFIX=/scratch4fun`

本项目的 `docker-compose.yml` 已默认设置该变量。

## 统一入口网关（推荐做法）

如果你希望多个服务（cc、bb 等）统一由一个 Nginx 网关对外提供 80/443，并统一管理证书与反代规则，请使用本仓库提供的网关模板：

- 网关部署说明：[GATEWAY.md](file:///e:/PersonalFiles/Coding/scratchforFun/ops/nginx-gateway/GATEWAY.md)
- cc（刮刮卡）接入说明：[CC_SCRATCH_APP.md](file:///e:/PersonalFiles/Coding/scratchforFun/ops/nginx-gateway/CC_SCRATCH_APP.md)
- bb 服务接入事项清单：[BB_SERVICE_STEPS.md](file:///e:/PersonalFiles/Coding/scratchforFun/ops/nginx-gateway/BB_SERVICE_STEPS.md)

### SSL/HTTPS 配置

1. **获取SSL证书**

```bash
# 使用Let's Encrypt (推荐)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/key.pem
sudo chown $USER:$USER ./ssl/*
```

2. **启用HTTPS**

编辑 `nginx.conf`，取消HTTPS服务器配置的注释。

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f scratch-app  # 只看应用日志

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新应用
git pull
docker compose build
docker compose up -d scratch-app

# 备份数据库
cp ./data/xx.sqlite ./data/xx.sqlite.backup.$(date +%Y%m%d_%H%M%S)

# 进入容器调试
docker-compose exec scratch-app bash
```

## 监控和维护

### 日志管理

```bash
# 查看实时日志
docker-compose logs -f

# 限制日志大小（在docker-compose.yml中添加）
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 性能监控

```bash
# 查看资源使用情况
docker stats

# 查看容器详细信息
docker-compose exec scratch-app top
```

### 自动备份

创建备份脚本 `backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp xx.sqlite $BACKUP_DIR/database_$DATE.sqlite
cp -r data $BACKUP_DIR/data_$DATE

# 删除7天前的备份
find $BACKUP_DIR -name "*" -mtime +7 -delete
```

添加到crontab：
```bash
crontab -e
# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

## 故障排除

### 常见问题

1. **端口被占用**
```bash
# 查看端口占用
sudo netstat -tlnp | grep :5000
# 修改docker-compose.yml中的端口映射
```

2. **权限问题**
```bash
# 确保文件权限正确
sudo chown -R $USER:$USER .
chmod +x deploy.sh
```

3. **数据库问题**
```bash
# 重新初始化数据库
rm xx.sqlite
docker-compose restart
```

4. **内存不足**
```bash
# 增加swap空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 获取帮助

如果遇到问题，请检查：
1. Docker和docker-compose版本
2. 服务器资源使用情况
3. 防火墙和网络配置
4. 应用日志输出

## 安全建议

1. **定期更新**
   - 定期更新Docker镜像
   - 更新系统安全补丁

2. **访问控制**
   - 使用强密码
   - 限制管理员访问IP
   - 启用HTTPS

3. **数据备份**
   - 定期备份数据库
   - 异地存储备份文件

4. **监控告警**
   - 设置服务监控
   - 配置异常告警
