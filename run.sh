#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 激活虚拟环境并运行应用
source "$SCRIPT_DIR/venv/bin/activate" && python "$SCRIPT_DIR/app.py" 