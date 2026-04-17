#!/bin/bash
# 光储柴微网每日知识采集任务

cd /root/.openclaw/workspace

# 获取今日日期
TODAY=$(date +%Y-%m-%d)

cat > /tmp/pv_microgrid_task.json << 'EOF'
{
  "cron": "0 9 * * *",
  "name": "光储柴微网每日知识简报",
  "description": "自动搜集光储柴微网领域最新技术、项目、政策动态，生成知识简报",
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "content": "请搜集关于'光储柴微网'、'光伏储能微电网'、'光储柴一体化'等领域的最新信息（技术进展、标杆项目、政策动态、市场趋势），整理成一份结构化的知识简报，包括：1）今日热点 2）技术前沿 3）项目案例 4）政策补贴 5）学习要点。用中文输出，格式清晰。"
  },
  "delivery": {
    "mode": "announce",
    "to": "kimi-claw"
  }
}
EOF

echo "任务配置已生成: /tmp/pv_microgrid_task.json"
