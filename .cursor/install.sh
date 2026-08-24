#!/usr/bin/env bash
# Shannon OS Agent —— Cloud Agent 环境安装脚本
# 作用：为云端开发环境准备后端 Python 依赖与前端构建产物。
# 该脚本必须是幂等的：可重复运行且不产生副作用。
set -euo pipefail

# 定位仓库根目录（脚本位于 <repo>/.cursor/ 下）
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 1. 确保 python venv 系统包可用（Cursor 默认镜像未预装 python3-venv）
#    使用 ensurepip 探测，缺失则通过 apt 安装，保持幂等。
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "[install] 安装 python3-venv 系统包..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv
fi

# 2. 创建/复用虚拟环境并安装后端依赖
if [ ! -x ".venv/bin/python" ]; then
  echo "[install] 创建 Python 虚拟环境 .venv ..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "[install] 安装后端依赖 (requirements.txt) ..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. 安装前端依赖并构建（FastAPI 直接托管 web/dist 静态产物）
echo "[install] 安装前端依赖 (npm ci) ..."
cd web
npm ci
echo "[install] 构建前端 (npm run build) ..."
npm run build

echo "[install] 安装完成。"
