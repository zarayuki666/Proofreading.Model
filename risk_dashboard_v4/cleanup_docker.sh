#!/usr/bin/env bash
# cleanup_docker.sh
# 自动清理 Docker 无用资源与 pip 缓存，并显示清理前后磁盘使用。
# 使用： chmod +x cleanup_docker.sh && sudo ./cleanup_docker.sh

set -euo pipefail

echo "===== Docker & Disk Cleanup 脚本 ====="
echo
echo "⚠️ 注意：此脚本将删除停止的容器、未使用的镜像、构建缓存。"
echo "如果你不想清理，请按 Ctrl+C 取消。5 秒后继续..."
sleep 5

echo
echo ">>> 🧭 清理前磁盘使用情况 (df -h /)"
df -h /
echo
echo ">>> 🐳 Docker 使用概览 (docker system df)"
docker system df || true
echo
read -p "继续执行自动清理？ (y/N) " CONFIRM
CONFIRM=${CONFIRM:-N}
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "🚫 已取消，无任何更改。"
  exit 0
fi

echo
echo ">>> 🧹 1) 删除已停止的容器"
docker container prune -f || true

echo ">>> 🧹 2) 删除未被使用的镜像"
docker image prune -a -f || true

echo ">>> 🧹 3) 删除构建缓存"
docker builder prune -a -f || true

echo
read -p "是否执行更彻底清理（包括未使用的 volumes）？ (y/N) " DEEP
DEEP=${DEEP:-N}
if [[ "$DEEP" =~ ^[Yy]$ ]]; then
  echo ">>> ⚙️ 4) docker system prune -a --volumes"
  docker system prune -a --volumes -f || true
else
  echo "跳过卷清理，仅删除镜像和缓存。"
fi

echo
echo ">>> 🧽 5) 清理 pip 缓存"
if [ -d "/root/.cache/pip" ]; then
  rm -rf /root/.cache/pip && echo "已删除 /root/.cache/pip"
fi
if [ -d "$HOME/.cache/pip" ]; then
  rm -rf "$HOME/.cache/pip" && echo "已删除 $HOME/.cache/pip"
fi

echo
echo ">>> ✅ 清理完成，结果如下："
echo
df -h /
echo
docker system df || true
echo
echo "🎯 清理结束。建议：定期执行此脚本保持 Docker 环境干净。"
