# SkyEye 快速启动指南

## 🚀 初次运行项目必须执行的命令

### 1. 环境设置
```bash
# 设置虚拟环境（如果还没有）
uv venv .venv
source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt

# 初始化git子模块（protobuf定义）
git submodule update --init --recursive

# 编译protobuf文件
bash scripts/utils/proto_compile.sh
```

### 2. 启动基础服务
```bash
# 启动PostgreSQL和Redis服务
./scripts/local/manage_docker.sh up

# 检查服务状态
./scripts/local/manage_docker.sh status
```

### 3. 数据库初始化
```bash
# 创建数据库迁移
uv run python manage.py makemigrations

# 应用数据库迁移
uv run python manage.py migrate
```

### 4. 启动后台任务服务
```bash
# 启动所有Celery服务（worker + beat）
./scripts/local/manage_celery.sh start

# 初始化定时任务
./scripts/local/manage_celery.sh init-tasks
```

### 5. 启动API服务
```bash
# 启动Django开发服务器
uv run python manage.py runserver
```

## ⚡ 日常启动命令（已配置环境后）

```bash
# 1. 启动基础设施
./scripts/local/manage_docker.sh up

# 2. 启动后台任务服务
./scripts/local/manage_celery.sh start

# 3. 启动API服务
uv run python manage.py runserver
```

## 📊 验证接口数据

### 等待数据收集
初次启动后，需要等待一段时间让系统收集数据：
- **批量请求任务**（每2秒执行）开始收集数据
- **数据同步任务**（每1秒执行）将数据持久化到数据库

### 测试接口
```bash
# 测试市场数据接口（可能需要等待几分钟有数据）
curl "http://localhost:8000/api/v1/cmc/market-data?cmc_id=1"

# 如果返回空，可以手动触发数据收集
curl "http://localhost:8000/api/v1/cmc/market-data?cmc_id=1"
```

## 🔧 常用管理命令

### Celery服务管理
```bash
# 查看所有服务状态
./scripts/local/manage_celery.sh status

# 查看日志
./scripts/local/manage_celery.sh logs

# 重启所有服务
./scripts/local/manage_celery.sh restart

# 停止所有服务
./scripts/local/manage_celery.sh stop

# 启动监控UI
./scripts/local/manage_celery.sh flower
```

### 数据库和Redis管理
```bash
# 查看Docker服务状态
./scripts/local/manage_docker.sh status

# 停止Docker服务
./scripts/local/manage_docker.sh down

# 重启Docker服务
./scripts/local/manage_docker.sh up
```

## ⚠️ 重要注意事项

1. **环境变量**：确保在 `.env` 或环境中配置了 `COINMARKETCAP_API_KEY`
2. **数据库配置**：确保 `skyeye/local_settings.py` 中数据库配置正确
3. **首次数据收集**：API接口可能需要几分钟才会有数据返回
4. **服务顺序**：必须按照上述顺序启动服务，确保依赖关系正确

## 🚨 故障排除

### 如果遇到问题
```bash
# 检查Celery状态
./scripts/local/manage_celery.sh status

# 查看详细日志
./scripts/local/manage_celery.sh logs

# 检查Redis数据
redis-cli -h localhost -p 6379 -n 1 KEYS "cmc:quote_data:*" | wc -l
redis-cli -h localhost -p 6379 -n 1 FLUSHDB
# 清空所有数据库
redis-cli -h localhost -p 6379 FLUSHALL

# 完全重启系统
./scripts/local/manage_celery.sh stop
./scripts/local/manage_docker.sh down
./scripts/local/manage_docker.sh up
./scripts/local/manage_celery.sh start
./scripts/local/manage_celery.sh init-tasks
```

### 常见问题
- **接口返回空数据**：等待2-3分钟让定时任务收集数据
- **Celery连接错误**：检查Redis服务是否正常运行
- **数据库连接错误**：检查PostgreSQL服务是否正常运行
- **任务不执行**：检查是否已执行 `init-tasks` 命令

按照这个指南，你的SkyEye项目应该能够快速启动并正常工作！