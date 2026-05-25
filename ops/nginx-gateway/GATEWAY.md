# 统一入口 Nginx（网关）部署

目标：在服务器新建独立目录（例如 `/opt/nginx-gateway`）部署一个 Nginx 网关容器，统一接入多个服务（示例：scratch-app=刮刮卡、warehouse=仓库系统），并统一签发/续期 HTTPS 证书。

## 一、准备（必须先做）

### 1) 创建目录（服务器上执行）

```bash
mkdir -p /opt/nginx-gateway
```

将本仓库的目录复制到服务器（你说“不上 git”，可以用 scp/rsync）：

```bash
scp -r ./ops/nginx-gateway/* user@server:/opt/nginx-gateway/
```

### 2) 创建外部 Docker 网络（服务器上执行一次）

```bash
docker network create gateway-network
```

该网络用于让网关容器跨项目反代到不同 compose 里的服务容器（cc、bb 等）。

## 二、配置网关

编辑 `/opt/nginx-gateway/conf.d/default.conf`：
- 将域名替换为你的真实子域名（当前默认示例已使用 `scratch-app.hchch.tech`、`warehouse.hchch.tech`）
- 确保 upstream 指向的容器名与各服务 compose 里的 `container_name` 一致
  - scratch-app 容器名：`cc-service`（刮刮卡）
  - warehouse 容器名：`warehouse-nginx`（仓库系统的应用入口）

## 三、启动网关（HTTP）

```bash
cd /opt/nginx-gateway
docker compose up -d nginx-gateway
```

此时 HTTP(80) 会用于 ACME 的 http-01 challenge。

## 四、签发证书（推荐 http-01，简洁）

在服务器上执行（会把挑战文件写入 `./certbot/www`，由 Nginx 提供）：

```bash
cd /opt/nginx-gateway
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  -d scratch-app.hchch.tech \
  --email your@email.com --agree-tos --no-eff-email
```

为 bb 也申请一次：

```bash
cd /opt/nginx-gateway
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  -d warehouse.hchch.tech \
  --email your@email.com --agree-tos --no-eff-email
```

## 五、启用 HTTPS

`default.conf` 中已包含 443 配置，证书存在后重启网关即可：

```bash
cd /opt/nginx-gateway
docker compose restart nginx-gateway
docker compose up -d certbot
```

## 六、防火墙

放通 80/443（网关需要对外提供服务）：
- Ubuntu：`ufw allow 80 && ufw allow 443`
- CentOS：`firewall-cmd --permanent --add-service=http --add-service=https && firewall-cmd --reload`

## 七、验证

- `https://scratch-app.hchch.tech/` 应该进入刮刮卡
- `https://warehouse.hchch.tech/` 应该进入仓库系统

如果某个服务挂掉，另外的域名仍应可访问（网关只是入口，不应互相影响）。
