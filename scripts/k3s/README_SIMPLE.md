# SkyEye Ubuntu Celery 管理脚本

这是一个简化版的 Celery 管理脚本，专为 Ubuntu 服务器环境设计，解决了原 `manage_celery.sh` 脚本中 Mac 特定命令的兼容性问题。

## 🚀 核心功能

### 启动所有 Celery 服务
```bash
./scripts/k3s/manage_celery_k3s.sh start
```
等同于原来的：
```bash
./scripts/local/manage_celery.sh start
```

### 初始化定时任务
```bash
./scripts/k3s/manage_celery_k3s.sh init-tasks
```
等同于原来的：
```bash
./scripts/local/manage_celery.sh init-tasks
```

## 📋 所有可用命令

```bash
# 启动所有服务（worker + beat）
./scripts/k3s/manage_celery_k3s.sh start

# 停止所有服务
./scripts/k3s/manage_celery_k3s.sh stop

# 重启所有服务
./scripts/k3s/manage_celery_k3s.sh restart

# 查看服务状态
./scripts/k3s/manage_celery_k3s.sh status

# 初始化定时任务
./scripts/k3s/manage_celery_k3s.sh init-tasks

# 查看日志
./scripts/k3s/manage_celery_k3s.sh logs

# 帮助信息
./scripts/k3s/manage_celery_k3s.sh help
```

## 🔧 Ubuntu 兼容性改进

### CPU 核心检测
- **原版**：使用 `sysctl -n hw.physicalcpu`（Mac 特定）
- **Ubuntu 版**：使用 `nproc`（Linux 标准）

### 进程管理
- **原版**：可能使用 `killall`
- **Ubuntu 版**：使用 `pkill`（更好的兼容性）

### 虚拟环境
- **原版**：检查 `uv venv`
- **Ubuntu 版**：兼容 `python3 -m venv`

## 🚀 典型使用流程

### 日常启动
```bash
# 1. 启动基础设施（如果使用 Docker）
./scripts/local/manage_docker.sh up

# 2. 启动 Celery 服务
./scripts/k3s/manage_celery_k3s.sh start

# 3. 初始化任务（首次运行或需要重新初始化时）
./scripts/k3s/manage_celery_k3s.sh init-tasks

# 4. 启动 Django 服务
python manage.py runserver
```

### 检查状态
```bash
# 查看服务状态
./scripts/k3s/manage_celery_k3s.sh status

# 查看日志
./scripts/k3s/manage_celery_k3s.sh logs
```

## 📁 文件位置

```
scripts/k3s/
├── manage_celery_k3s.sh    # Ubuntu 兼容的 Celery 管理脚本
└── README_SIMPLE.md        # 本文档
```

## ⚠️ 注意事项

1. **Python 环境**：确保系统已安装项目所需的 Python 依赖
2. **依赖服务**：确保 PostgreSQL 和 Redis 服务正在运行
3. **权限**：脚本需要可执行权限（已设置）
4. **日志目录**：脚本会自动创建 `./logs` 目录

## 🔍 故障排除

### Python 依赖未安装
```bash
# 安装项目依赖
pip install -r requirements.txt
# 或使用系统包管理器安装
```

### 服务无法启动
```bash
# 检查状态
./scripts/k3s/manage_celery_k3s.sh status

# 查看详细日志
./scripts/k3s/manage_celery_k3s.sh logs

# 检查 Redis 和 PostgreSQL
./scripts/local/manage_docker.sh status
```

### 清理和重启
```bash
# 停止所有服务
./scripts/k3s/manage_celery_k3s.sh stop

# 重新启动
./scripts/k3s/manage_celery_k3s.sh start
```

这个简化版脚本专注于核心功能，去除了复杂的 K3s 部署功能，使其更易用且在 Ubuntu 环境下完全兼容。