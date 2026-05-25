# cc 服务（Scratch App）接入网关的操作

目标：cc 服务对应本仓库的 `scratch-app`（Flask），通过统一入口 Nginx 网关以 `https://scratch-app.hchch.tech/` 的方式访问。

## 一、部署前的关键点

1. cc 容器需要加入 `gateway-network` 外部网络，供网关容器反代访问。
2. cc 对外不再需要 `ports: "5000:5000"`（可以保留用于临时调试，但生产建议去掉，避免端口冲突/暴露）。
3. cc 建议用“子域名根路径”访问（例如 `https://scratch-app.hchch.tech/`），因此：
   - `URL_PREFIX` 建议设置为空

## 二、cc 服务 docker-compose.yml 建议改法

在服务器 `cc` 服务目录（例如 `/opt/cc-service`）中：

1) 让容器名与网关一致（默认网关配置使用 `cc-service`）：

```yaml
services:
  scratch-app:
    container_name: cc-service
```

2) 加入外部网络 + 仅 expose 内部端口：

```yaml
services:
  scratch-app:
    expose:
      - "5000"
    networks:
      - gateway-network
      - cc-internal-network
```

3) 底部网络定义：

```yaml
networks:
  gateway-network:
    external: true
  cc-internal-network:
    driver: bridge
```

4) 环境变量建议：

```yaml
environment:
  - PORT=5000
  - URL_PREFIX=
  - DATABASE_FILE=/app/data/xx.sqlite
  - SETTINGS_FILE=/app/data/setting.json
```

## 三、启动/重启

```bash
docker compose down
docker compose up -d
```

## 四、验证

1) 先确认 cc 容器已经在网关网络中：
```bash
docker network inspect gateway-network | grep cc-service
```

2) 浏览器访问：
- `https://scratch-app.hchch.tech/`

如果看到页面但静态资源 404，优先检查：
- `URL_PREFIX` 是否为空
- 网关的 server_name / upstream 容器名是否一致
