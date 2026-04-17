#!/bin/bash
# OpenClaw Workspace 自动备份脚本
# 备份用户why的专业方向数据到GitHub

# 配置
GITHUB_REPO="git@github.com:haoyuwang971/openclaw-backup.git"
BACKUP_DIR="/root/.openclaw/workspace"
DATE=$(date +%Y-%m-%d_%H:%M:%S)
COMMIT_MSG="Auto backup: $DATE"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}开始备份 OpenClaw Workspace...${NC}"
echo "备份时间: $DATE"

# 检查Git是否安装
if ! command -v git &> /dev/null; then
    echo -e "${RED}错误: Git未安装${NC}"
    echo "请运行: apt-get update && apt-get install -y git"
    exit 1
fi

# 检查备份目录是否存在
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}错误: 备份目录不存在: $BACKUP_DIR${NC}"
    exit 1
fi

cd "$BACKUP_DIR"

# 初始化Git仓库（如果不存在）
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}初始化Git仓库...${NC}"
    git init
    git remote add origin "$GITHUB_REPO"
fi

# 配置Git用户信息（如果不存在）
if ! git config --get user.name &> /dev/null; then
    git config user.name "OpenClaw Backup Bot"
    git config user.email "backup@openclaw.local"
fi

# 添加文件到暂存区
echo -e "${YELLOW}添加文件...${NC}"

# 只备份关键目录，排除大文件和敏感信息
git add memory/ --ignore-errors 2>/dev/null
git add users/why/ --ignore-errors 2>/dev/null
git add *.md --ignore-errors 2>/dev/null
git add *.json --ignore-errors 2>/dev/null
git add AGENTS.md --ignore-errors 2>/dev/null
git add USER.md --ignore-errors 2>/dev/null

# 检查是否有变更要提交
if git diff --cached --quiet; then
    echo -e "${GREEN}没有变更需要备份${NC}"
    exit 0
fi

# 提交
echo -e "${YELLOW}提交变更...${NC}"
git commit -m "$COMMIT_MSG"

# 推送到GitHub
echo -e "${YELLOW}推送到GitHub...${NC}"
if git push origin main 2>/dev/null || git push origin master 2>/dev/null; then
    echo -e "${GREEN}✅ 备份成功!${NC}"
    echo "提交信息: $COMMIT_MSG"
else
    echo -e "${RED}❌ 推送失败${NC}"
    echo "可能原因:"
    echo "  1. 未配置SSH密钥"
    echo "  2. 仓库地址错误"
    echo "  3. 网络问题"
    exit 1
fi
