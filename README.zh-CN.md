# TeamNav

[English](README.md) | [简体中文](README.zh-CN.md)

TeamNav 是一个面向个人和团队、支持自托管与公开分享的导航主页。创建工作台后会得到一个公开访问链接和一个独立且难以猜测的管理链接。账号不是必需的；注册登录后，可以把多个工作台同步到个人账号中统一管理。

## 主要功能

- 支持匿名或登录账号创建工作台，内置七种模板、明暗主题和可选的公开访问密码
- 公开访问链接与私密管理链接分离，支持二维码分享和下载恢复文件
- 支持邮箱账号、工作台归属、认领已有工作台及跨设备管理
- 响应式公开导航页，支持本地搜索、可拖动分类导航、站点图标、点击统计和复制链接
- 可自定义品牌色、明暗模式、背景画布、卡片样式、页面宽度、列数、密度和内容显示方式
- 使用 HttpOnly 管理会话和 CSRF 防护
- 支持站点、分类和书签编辑，目录折叠、跨目录拖动、批量标签和实时预览
- 支持原子化 JSON/浏览器书签导入导出、容量错误提示、克隆和基础日统计
- 根据浏览器语言自动选择中文或英文，也可以手动切换并保存偏好
- 书签导入前可预览合并/覆盖、重复项处理和容量检查结果
- 支持链接健康检查、按工作台启用的自动维护和可恢复的修改历史
- 支持验证码、滥用举报、管理员处理和站点封禁
- 支持单镜像 SQLite 部署，也支持拆分式 SQLite、PostgreSQL 和 MySQL，并自动执行数据库迁移

## 项目结构

- `apps/web`：Next.js 16、React 19 和 TypeScript 前端
- `apps/api`：FastAPI、SQLAlchemy 2 和 Alembic 后端
- `packages/templates`：带版本的内置模板
- `docs`：架构、运维和安全说明

详细资料见[架构说明](docs/architecture.md)、[中文运维说明](docs/operations.zh-CN.md)和[安全说明](docs/security.md)。
公开镜像也可以直接从 Docker Hub 拉取：[一体化镜像](https://hub.docker.com/r/glfc2b/teamnav-aio)、
[API 镜像](https://hub.docker.com/r/glfc2b/teamnav-api)和[前端镜像](https://hub.docker.com/r/glfc2b/teamnav-web)。

## 本地开发

环境要求：Node.js 24+ 和 Python 3.12+。

```bash
npm install
npm run dev
```

另开一个终端运行后端：

```bash
python -m venv .venv
.venv/Scripts/pip install -e "apps/api[dev]" # Windows
cd apps/api
set DATABASE_URL=sqlite+aiosqlite:///./teamnav.db
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

在 macOS/Linux 上请启用 `.venv/bin/activate`，并使用 `export DATABASE_URL=...`。

打开 `http://localhost:3000`。前端默认连接 `http://localhost:8000`；如需修改，请在构建前设置 `NEXT_PUBLIC_API_URL`。

## Docker 部署

将 `.env.example` 复制为 `.env`，并为 `SECRET_KEY` 和 `ADMIN_TOKEN` 设置各自唯一的强随机值。默认 Compose 部署只暴露 `http://localhost:3000` 一个网关，API 请求使用同源转发到内部 API 容器。

### 一体化单镜像部署

最简单的安装方式是使用已经发布的一体化镜像。镜像包含 Nginx、前端、API 和 SQLite，应用数据保存在 Docker 命名卷中：

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
```

网站地址为 `http://localhost:3000`，只会创建一个应用容器。需要连接外部 PostgreSQL 或 MySQL 时，在启动同一个 AIO 部署前设置 `DATABASE_URL` 即可。

每个工作台默认最多支持 200 个目录和 2,000 个书签。部署者可以通过 `MAX_CATEGORIES_PER_SITE` 和 `MAX_LINKS_PER_SITE` 修改限制。

自动链接检查需要在每个工作台中主动开启。部署级调度可以通过 `LINK_CHECK_SCHEDULER_ENABLED`、
`LINK_CHECK_POLL_SECONDS`、`LINK_CHECK_TIMEOUT_SECONDS` 和 `LINK_CHECK_BATCH_SIZE` 调整。
默认禁止检查本机和私有网络地址；只有在可信内网部署中才应设置
`LINK_CHECK_ALLOW_PRIVATE_NETWORKS=true`。

等价的 Docker 命令如下：

```bash
docker volume create teamnav-data
docker run -d --name teamnav --restart unless-stopped \
  --env-file .env \
  -p 3000:8080 \
  -v teamnav-data:/data \
  glfc2b/teamnav-aio:latest
```

更新一体化部署且保留数据：

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
```

Docker 会重新创建应用容器并复用数据卷。入口脚本会先执行向前数据库迁移，再开始提供服务，并在停止时正确关闭内部进程。这是短暂重启，不是零停机热更新。Watchtower 等自动更新工具需要访问 Docker Socket，因此项目默认不会启用。

### 拆分式部署

直接拉取已发布的镜像，不在本机构建：

```bash
docker compose pull
docker compose up -d --no-build
```

轻量拆分式 SQLite，适合单实例：

```bash
docker compose pull
docker compose up -d --no-build
```

内置 PostgreSQL，推荐用于正式环境：

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml pull
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --no-build
```

内置 MySQL：

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml pull
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --no-build
```

使用外部 PostgreSQL 或 MySQL 时，在 `.env` 中设置 `DATABASE_URL`，然后使用基础命令。此时 SQLite 数据卷仍会挂载，但不会使用。`.env.example` 中提供了连接示例。API 容器每次启动时都会自动迁移数据库表。

### 从源码构建镜像

克隆仓库，复制环境变量文件，然后在本地构建并启动一体化镜像：

```bash
git clone https://github.com/kevincai100/TeamNav.git
cd TeamNav
cp .env.example .env
docker compose -f docker-compose.aio.yml build --pull
docker compose -f docker-compose.aio.yml up -d
```

构建拆分式前端和 API 镜像：

```bash
docker compose build --pull
docker compose up -d
```

`main` 分支构建的镜像会同时发布为 `main` 和 `latest`。`v0.1.0` 等版本标签还会发布对应的语义化版本镜像。正式环境可以把 `TEAMNAV_VERSION` 固定到具体版本，而不是一直跟随 `latest`。

公网部署时必须启用 TLS，把 `APP_URL` 和 `CORS_ORIGINS` 设置为公网网关地址，并设置 `COOKIE_SECURE=true`。为保证镜像可移植，`NEXT_PUBLIC_API_URL` 应保持为空。升级、备份和恢复步骤见[中文运维说明](docs/operations.zh-CN.md)。

数据库原生备份只能恢复到相同类型的数据库。SQLite 迁移到 PostgreSQL 或 MySQL 属于跨数据库数据迁移，不是直接恢复数据库文件。

## 验证命令

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm run e2e

cd apps/api
../../.venv/Scripts/python -m pytest -q
../../.venv/Scripts/ruff check app tests alembic
```

## 当前 MVP 范围

当前 MVP 已包含匿名与账号归属、公开分享、管理、访问保护、内容治理、导入导出、统计和自托管。组织系统、多人同时编辑、SSO、订阅和自定义域名暂不在范围内。

## 参与贡献与安全问题

欢迎参与贡献。提交 Pull Request 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全漏洞不要发到公开 Issue，请按照 [SECURITY.md](SECURITY.md) 的说明，通过 GitHub Security Advisories 私密报告。每次推送和 Pull Request 都会进行已提交密钥扫描，扫描通过后才能发布容器镜像。

## 许可证与品牌

TeamNav 源代码使用 [GNU Affero General Public License v3.0 或更高版本](LICENSE)。如果把修改后的版本作为网络服务提供给用户，AGPL 要求向这些用户提供对应源代码。软件许可证不授予 TeamNav 名称和品牌的使用权，具体见 [TRADEMARKS.md](TRADEMARKS.md)。

版权所有 (C) 2026 TeamNav 贡献者。
