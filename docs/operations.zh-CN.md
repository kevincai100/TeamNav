# 运维说明

## 安装

把 `.env.example` 复制为 `.env`，为 `SECRET_KEY` 和 `ADMIN_TOKEN` 设置各自唯一的长随机值，然后选择数据库模式。已发布镜像默认使用 Docker Hub 上公开的 `glfc2b/teamnav-*` 仓库。内置数据库密码会进入 `DATABASE_URL`，因此只应使用字母、数字、`.`、`_`、`~` 和 `-` 等 URL 安全字符。

一体化 SQLite 部署只运行一个应用容器：

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
```

AIO 镜像包含 Nginx、Next.js、FastAPI 和 SQLite，只暴露容器内的 `8080` 端口，数据库保存在 `teamnav-aio-data` 命名卷的 `/data` 目录。也可以通过 `DATABASE_URL` 连接外部 PostgreSQL 或 MySQL。

拆分式 SQLite：

```bash
docker compose pull
docker compose up -d --no-build
```

内置 PostgreSQL，推荐正式环境使用：

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml pull
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --no-build
```

内置 MySQL：

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml pull
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --no-build
```

使用外部数据库时，在 `.env` 中设置 `postgresql+asyncpg://` 或 `mysql+asyncmy://` 格式的 `DATABASE_URL`，密码中的保留字符必须进行 URL 编码。不要把 API、前端或数据库容器端口直接暴露到公网。

网站默认地址为 `http://localhost:3000`，就绪检查地址为 `http://localhost:3000/health/ready`。公网部署必须启用 TLS，把 `APP_URL` 和 `CORS_ORIGINS` 设置为公网地址，保持 `NEXT_PUBLIC_API_URL` 为空，并设置 `COOKIE_SECURE=true`。

## 升级

1. 先备份数据库。
2. 拉取新的源码或镜像版本。
3. 已发布镜像执行 `docker compose pull`，源码部署执行 `docker compose build --pull`。
4. 执行 `docker compose up -d`；API 会在提供服务前自动执行向前迁移。
5. 检查 `/health/ready`、账号会话恢复和公开创建流程。

AIO 完整更新命令：

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
docker compose -f docker-compose.aio.yml ps
```

容器被替换后命名卷仍会保留。AIO 更新会产生一次短暂重启，并不是零停机热更新。需要零停机时，应使用拆分式部署和外部数据库。

## 备份与恢复

先创建不会提交到 Git 的本地备份目录，并把加密后的备份复制到其他机器或对象存储：

```bash
mkdir -p backups
```

数据库原生备份只能恢复到相同类型的数据库，不能把 SQLite 文件直接恢复到 PostgreSQL 或 MySQL。执行任何恢复前，都应再创建一份当前数据库备份。

### SQLite

AIO SQLite 备份：

```bash
docker compose -f docker-compose.aio.yml stop teamnav
docker compose -f docker-compose.aio.yml cp teamnav:/data/teamnav.db ./backups/teamnav-aio.db
docker compose -f docker-compose.aio.yml start teamnav
```

拆分式 SQLite 备份：

```bash
docker compose stop api
docker compose cp api:/data/teamnav.db ./backups/teamnav-sqlite.db
docker compose start api
```

AIO SQLite 恢复。命令会修复文件所有权、执行 SQLite 完整性检查，并等待应用完成数据库迁移：

```bash
docker compose -f docker-compose.aio.yml stop teamnav
docker compose -f docker-compose.aio.yml cp ./backups/teamnav-aio.db teamnav:/data/teamnav.db
docker compose -f docker-compose.aio.yml run --rm --no-deps --user root --entrypoint chown teamnav teamnav:teamnav /data/teamnav.db
docker compose -f docker-compose.aio.yml run --rm --no-deps --entrypoint python teamnav -c "import sqlite3; db=sqlite3.connect('/data/teamnav.db'); result=db.execute('PRAGMA integrity_check').fetchone()[0]; assert result == 'ok', result"
docker compose -f docker-compose.aio.yml up -d --wait
```

拆分式 SQLite 恢复使用相同流程，将 Compose 文件改为 `docker-compose.yml`，服务名从 `teamnav` 改为 `api`。

### PostgreSQL

创建压缩备份：

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres sh -ceu 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/teamnav.dump'
docker compose -f docker-compose.yml -f docker-compose.postgres.yml cp postgres:/tmp/teamnav.dump ./backups/teamnav-postgres.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres rm -f /tmp/teamnav.dump
```

恢复前停止 API，并先使用 `pg_restore --list` 检查备份格式：

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml stop api
docker compose -f docker-compose.yml -f docker-compose.postgres.yml cp ./backups/teamnav-postgres.dump postgres:/tmp/teamnav.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres pg_restore --list /tmp/teamnav.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres sh -ceu 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges --exit-on-error --single-transaction /tmp/teamnav.dump'
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres rm -f /tmp/teamnav.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --wait
```

### MySQL

创建事务一致的 SQL 备份：

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql sh -ceu 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -u "$MYSQL_USER" --single-transaction --quick --routines --triggers --hex-blob --no-tablespaces "$MYSQL_DATABASE" > /tmp/teamnav.sql'
docker compose -f docker-compose.yml -f docker-compose.mysql.yml cp mysql:/tmp/teamnav.sql ./backups/teamnav-mysql.sql
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql rm -f /tmp/teamnav.sql
```

停止 API，重建空的 `teamnav` 数据库并恢复：

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml stop api
docker compose -f docker-compose.yml -f docker-compose.mysql.yml cp ./backups/teamnav-mysql.sql mysql:/tmp/teamnav.sql
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql sh -ceu 'test -s /tmp/teamnav.sql; MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root -e "DROP DATABASE IF EXISTS teamnav; CREATE DATABASE teamnav CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"; MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root teamnav < /tmp/teamnav.sql'
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql rm -f /tmp/teamnav.sql
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --wait
```

备份中包含账号密码和管理能力密钥的哈希。必须限制访问并加密备份，同时定期在隔离环境演练恢复。管理页面导出的单个工作台 JSON 不包含这些敏感数据。

## 恢复文件与密钥轮换

创建工作台时下载的恢复文件包含编辑密钥唯一可恢复的副本，应保存在密码管理器中。数据库只保存哈希，管理员无法反推出原始编辑密钥。密钥泄漏后应在管理页面执行轮换，现有管理会话会全部失效。
