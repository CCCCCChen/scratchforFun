# 自制娱乐刮刮卡 (Scratch Card App)

这是一个基于 Flask 开发的移动端优先的在线刮刮卡应用。它模拟了真实的刮卡体验（Canvas 刮开），并提供管理后台用于配置与用户管理。

## 功能特点

*   轻量 Dashboard：纯 HTML/CSS + 服务端分页，适配 1 核 1G 服务器
*   刮卡体验：Canvas 刮开，达到阈值自动判定完成并落库
*   智能奖池：基于动态规划生成奖金分配
*   管理后台：
    *   保存配置并重置系统（重置票据与奖池，不删除用户账户）
    *   新建/删除用户、重置用户密码（删除用户不会清理其历史 owner_username 记录）
    *   用户/管理员密码均为哈希存储（不再明文保存）

## 快速开始

### 1. 环境准备

确保你的系统已安装 Python 3.8 或更高版本。

```bash
# 克隆或下载本项目到本地
cd scratchforFun
```

### 2. 安装依赖

本项目依赖较少，建议创建虚拟环境后安装：

```bash
# 创建虚拟环境 (可选)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装 Flask
pip install flask
```

*(注：本项目主要依赖 Flask，以及 Python 内置的 sqlite3, json, random 等库)*

### 3. 运行应用

```bash
python3 app.py
```

启动成功后，终端会显示访问地址，通常为：
*   本地访问：`http://127.0.0.1:5000`
*   局域网访问：`http://<你的局域网IP>:5000`

## 使用指南

### 👤 普通用户
1.  打开首页，使用分配的账号登录。
2.  进入 **Dashboard**，通过滑动或搜索选择一张心仪的卡片。
3.  点击卡片进入刮奖页面，用手指或鼠标刮开涂层。
4.  中奖后系统会自动记录并统计。

### 管理员设置
- 默认管理员账号：`admin`
- 默认初始密码：`admin123`（可通过环境变量 `ADMIN_INIT_PASSWORD` 覆盖）
- 后台入口：`/admin`

## 项目结构

```
scratchforFun/
├── app.py              # 主程序入口
├── setting.json        # 配置文件 (自动生成)
├── xx.sqlite           # 数据库文件 (自动生成)
├── static/             # 静态资源 (CSS, JS, Images)
└── templates/          # HTML 模板
    ├── dashboard.html  # 选卡大厅
    ├── scratch_card.html # 刮卡页面
    └── ...
```

## 注意事项

*   **数据重置**：后台“保存配置并重置系统”会清空票据/奖池数据（不删除用户账户）。
*   **密码**：所有用户（含管理员）密码均为哈希存储；重置密码会生成新的明文密码并在后台页面提示一次。

## Docker + HTTPS + 子路径部署（/scratch4fun/）

### 1) 构建并上传（两种方式）

方式 A：在服务器上构建
```bash
git clone <your-repo-url>
cd scratchforFun
mkdir -p data
docker compose build
docker compose up -d
```

方式 B：本地构建后推送镜像仓库（示例）
```bash
docker build -t <your-registry>/scratch4fun:latest .
docker push <your-registry>/scratch4fun:latest
```
然后在服务器上修改 `docker-compose.yml` 使用该镜像并 `docker compose up -d`。

### 2) 数据持久化

`docker-compose.yml` 会将宿主机 `./data/` 目录挂载到容器 `/app/data/`，并将持久化文件放在该目录下：
- `./data/xx.sqlite`：数据库
- `./data/setting.json`：系统配置

### 3) 配置 Nginx（HTTPS + 域名 + 文件夹路径）

项目自带 `nginx.conf`，已按子路径 `/scratch4fun/` 反代配置。关键点：
- 应用容器需要 `URL_PREFIX=/scratch4fun`（compose 已默认设置）
- 访问示例：`https://hchch.tech/scratch4fun/`

证书建议使用 Let's Encrypt，在宿主机准备好证书后放入 `./ssl/`：
- `./ssl/cert.pem`
- `./ssl/key.pem`

然后取消 `nginx.conf` 中 HTTPS server 段落的注释，并在 `docker-compose.yml` 中启动 `nginx` 服务。

---
Enjoy your lucky scratch! 🎉
