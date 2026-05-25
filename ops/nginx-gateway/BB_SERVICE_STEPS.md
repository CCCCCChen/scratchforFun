# bb 服务接入网关：需要同事完成的事项清单

目标：bb（warehouse）服务通过统一入口网关以 `https://warehouse.hchch.tech/` 方式访问；warehouse 服务自身不再直接暴露 80/443。

## 一、前置确认

1) warehouse 入口容器对外监听的“容器内部端口”是多少（推荐让入口容器监听 `80`，由网关做 HTTPS）  
2) bb 服务是否需要 websocket / SSE（如有，需要在网关加对应 header/upgrade 配置）

## 二、bb 服务 docker-compose.yml 改动要点

在服务器 warehouse 服务目录（例如 `/opt/warehouse-service`）：

### 1) 设置 container_name（与网关 upstream 一致）

网关默认 upstream 写的是 `warehouse-nginx:80`，所以建议：

```yaml
services:
  <bb-service>:
    container_name: warehouse-nginx
```

### 2) 去掉 ports 映射，改为 expose（让网关来访问）

```yaml
services:
  <bb-service>:
    expose:
      - "80"
```

如果当前有：
```yaml
ports:
  - "80:80"
  - "443:443"
```
生产建议删除（或至少改成不对公网开放），避免与网关的 80/443 冲突。

### 3) 加入网关外部网络

```yaml
services:
  <bb-service>:
    networks:
      - gateway-network
      - bb-internal-network
```

并在文件底部增加：

```yaml
networks:
  gateway-network:
    external: true
  bb-internal-network:
    driver: bridge
```

## 三、重启与自检

```bash
docker compose down
docker compose up -d
```

确认容器在网关网络中：

```bash
docker network inspect gateway-network | grep warehouse-nginx
```

## 四、网关侧对应项（由网关维护者处理）

在 `/opt/nginx-gateway/conf.d/default.conf`：

- server_name：`warehouse.hchch.tech`
- upstream：`warehouse-nginx:80`
- proxy_pass：`http://bb_service`

## 五、访问验证

- `https://warehouse.hchch.tech/`

如出现 502：
- 入口容器名是否一致（warehouse-nginx）
- 入口服务内部端口是否正确（80）
- warehouse 容器是否已加入 `gateway-network`

## 六、warehouse-nginx（服务内部 Nginx）配置改动建议

网关已经统一处理：
- 80 -> 443 跳转
- TLS 证书与 https
- `/.well-known/acme-challenge/`（签发与续期）

因此 warehouse-nginx 作为“内部入口”建议只保留一个 HTTP server：
- 只 `listen 80;`
- 不要 `listen 443 ssl;`（否则没证书也没必要）
- 不要再写 `return 301 https://...`（由网关处理）
- `server_name` 建议用 `_`（接受任意 Host）

最小示例（保留你原先的前端静态与 /api 反代逻辑）：

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=init:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=llm:10m rate=1r/s;

server {
  listen 80;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;
  client_max_body_size 20m;

  location ~ ^/api/init/ {
    limit_req zone=init burst=10 nodelay;
    proxy_pass http://backend:18808;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
  }

  location = /api/llm/test {
    limit_req zone=llm burst=5 nodelay;
    proxy_request_buffering off;
    proxy_pass http://backend:18808;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 120s;
  }

  location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend:18808;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
  }

  location /uploads/ {
    client_max_body_size 20m;
    proxy_pass http://backend:18808;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
  }

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```
