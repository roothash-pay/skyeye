# SkyEye 项目脚本目录

这个目录包含了 SkyEye 项目的所有实用脚本，已按功能分类整理，便于查找和使用。

## 📁 目录结构

```
scripts/
├── local/          # 本地开发相关脚本
├── production/     # 生产部署相关脚本  
├── utils/          # 通用工具脚本
└── postgres/       # PostgreSQL 初始化脚本
```

---

## 🔧 本地开发脚本 (`local/`)

这些脚本用于本地开发环境的设置和管理。

### `setup_env.sh` - 环境初始化
```bash
bash scripts/local/setup_env.sh
```
**功能**: 
- 从 `.env.production.example` 创建 `.env` 文件
- 自动生成安全的 `SECRET_KEY`
- 检查并提示必需的环境变量配置
- 适合首次项目设置

### `manage_docker.sh` - Docker 服务管理
```bash
./scripts/local/manage_docker.sh up        # 启动PostgreSQL+Redis
./scripts/local/manage_docker.sh down      # 停止所有服务
./scripts/local/manage_docker.sh status    # 查看服务状态
./scripts/local/manage_docker.sh logs      # 查看服务日志
```
**功能**: 管理本地开发用的PostgreSQL主从数据库和Redis服务

### `manage_celery.sh` - Celery 任务管理
```bash
./scripts/local/manage_celery.sh start     # 启动所有服务 (worker + beat)
./scripts/local/manage_celery.sh stop      # 停止所有服务 (worker + beat)
./scripts/local/manage_celery.sh restart   # 重启所有服务
./scripts/local/manage_celery.sh status    # 检查所有服务状态
./scripts/local/manage_celery.sh logs      # 查看worker日志
./scripts/local/manage_celery.sh flower    # 启动监控UI
./scripts/local/manage_celery.sh init-tasks # 初始化定时任务
```
**功能**: 管理Celery异步任务处理系统，统一管理worker和beat调度器

### `quick_check.sh` - 系统状态检查
```bash
./scripts/local/quick_check.sh
```
**功能**: 快速检查本地开发环境的所有服务状态

---

## 🚀 生产部署脚本 (`production/`)

这些脚本用于生产环境的部署和配置。

### `prepare_production_data.sh` - 数据准备
```bash
./scripts/production/prepare_production_data.sh
```
**功能**: 
- 在本地环境完整测试所有功能
- 获取全量CMC数据（资产、行情、K线）
- 验证API接口响应
- 导出生产环境种子数据SQL文件

### `prepare_production_env.sh` - 环境配置调整
```bash
bash scripts/production/prepare_production_env.sh
```
**功能**: 
- 将开发环境的.env配置调整为生产环境
- 自动替换localhost为K3s服务名
- 调整端口和安全设置
- 自动备份原配置

### `production_deployment.sh` - 统一部署 ⭐
```bash
./scripts/production/production_deployment.sh [种子数据文件.sql]
```
**功能**: 
- 自动检测部署环境（Docker/K3s）
- 智能处理.env配置
- 自动种子数据导入
- 完整服务部署和验证
- **这是主要的生产部署入口脚本**

### `env_to_k8s.sh` - 环境变量转换
```bash
./scripts/production/env_to_k8s.sh [.env文件] [命名空间] [输出目录]
```
**功能**: 
- 将.env文件转换为K3s ConfigMap和Secret
- 自动区分敏感和非敏感信息
- 生成一键应用脚本

### `k3s_deployment.sh` - K3s专用部署（已合并）
```bash
# 注意：此脚本已合并到 production_deployment.sh 中
# 建议直接使用 production_deployment.sh
```

---

## 🛠️ 通用工具脚本 (`utils/`)

这些脚本提供各种实用功能。

### `check_env.py` - 环境验证
```bash
python scripts/utils/check_env.py
```
**功能**: 
- 检查所有必需的环境变量
- 验证Django设置配置
- 提供详细的错误信息和修复建议

### `generate_secret_key.sh` - 密钥生成
```bash
# 仅生成密钥
./scripts/utils/generate_secret_key.sh

# 自动更新到.env文件
./scripts/utils/generate_secret_key.sh --update-env
```
**功能**: 
- 使用Django官方方法生成安全的SECRET_KEY
- 可选择自动更新到.env文件

### `proto_compile.sh` - Protobuf编译
```bash
bash scripts/utils/proto_compile.sh
```
**功能**: 编译gRPC protobuf定义文件

### `check_timezone.py` - 时区检测
```bash
python scripts/utils/check_timezone.py
```
**功能**: 检测和验证系统时区配置

### `demonstrate_timezone.py` - 时区演示
```bash
python scripts/utils/demonstrate_timezone.py
```
**功能**: 演示时区分离设计的工作原理

---

## 🏃‍♂️ 快速开始指南

### 本地开发环境设置
```bash
# 1. 环境初始化
bash scripts/local/setup_env.sh

# 2. 启动依赖服务
./scripts/local/manage_docker.sh up

# 3. 数据库迁移
uv run python manage.py migrate

# 4. 启动Celery服务
./scripts/local/manage_celery.sh start

# 5. 启动Django开发服务器
uv run python manage.py runserver

# 6. 验证环境
./scripts/local/quick_check.sh
```

### 生产环境部署
```bash
# 1. 本地数据准备
./scripts/production/prepare_production_data.sh

# 2. 生产环境配置调整
bash scripts/production/prepare_production_env.sh

# 3. 一键生产部署
./scripts/production/production_deployment.sh skyeye_production_seed_*.sql
```

---

## 📋 使用场景对照

| 场景 | 使用脚本 | 说明 |
|------|----------|------|
| 首次项目设置 | `local/setup_env.sh` | 初始化开发环境 |
| 日常开发 | `local/manage_docker.sh`<br>`local/manage_celery.sh` | 管理本地服务 |
| 环境问题排查 | `utils/check_env.py`<br>`local/quick_check.sh` | 诊断和验证 |
| 生产数据准备 | `production/prepare_production_data.sh` | 本地测试+数据导出 |
| 生产环境部署 | `production/production_deployment.sh` | 一键部署到生产 |
| 密钥轮换 | `utils/generate_secret_key.sh` | 安全密钥管理 |

---

## ⚠️ 重要提醒

### 脚本运行要求
- **工作目录**: 所有脚本都必须从项目根目录运行
- **权限**: 脚本已设置执行权限
- **环境**: 需要安装uv包管理器和Docker

### 文档更新
- **STARTUP_GUIDE.md**: 本地开发完整指南
- **CLAUDE.md**: 项目开发指南和架构说明
- **scripts/README.md**: 本文档

### 路径调整
由于脚本重新组织，如果遇到路径错误，请使用新的分类路径：
- 原 `scripts/setup_env.sh` → `scripts/local/setup_env.sh`
- 原 `scripts/production_deployment.sh` → `scripts/production/production_deployment.sh`

---

## 🆘 故障排除

### 常见问题

1. **脚本路径错误**
   ```bash
   # 检查脚本是否存在
   ls scripts/local/
   ls scripts/production/
   ls scripts/utils/
   ```

2. **权限问题**
   ```bash
   chmod +x scripts/*/*.sh
   chmod +x scripts/*/*/*.sh
   ```

3. **环境变量问题**
   ```bash
   python scripts/utils/check_env.py
   ```

4. **Docker服务问题**
   ```bash
   ./scripts/local/manage_docker.sh status
   ```

如需更多帮助，请参考项目文档或提交Issue。