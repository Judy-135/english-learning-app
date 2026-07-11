#!/bin/bash
# CloudStudio / 通用启动脚本：监听 0.0.0.0，端口取自 PORT 环境变量（默认 8000）
exec python3 deepl_proxy.py "${PORT:-8000}"
