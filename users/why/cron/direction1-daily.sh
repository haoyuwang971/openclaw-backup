#!/bin/bash
# why用户 - 方向1：新能源微网EMS - 每日技术简报

# 执行时间：每日 09:00
# 内容：搜集EMS算法、控制策略、拓扑、构网型技术最新进展

cd /root/.openclaw/workspace

PAYLOAD=$(cat <<'EOF'
{
  "cron": "0 9 * * *",
  "name": "why-direction1-ems-daily",
  "description": "why用户-方向1：新能源微网EMS每日技术简报",
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "content": "用户why的方向1（新能源微网-EMS）每日技术简报任务。请搜集以下领域的最新技术进展：1）EMS能量管理算法（MPC、优化调度）2）控制策略（VSG、构网型控制、下垂控制）3）拓扑结构（DC/AC耦合、光储柴架构）4）建模与仿真方法。整理成技术简报，保存到 users/why/direction-1-ems/briefs/ 目录，文件命名格式：YYYY-MM-DD-tech-brief.md。输出需专业、有深度，适合EMS产品实现参考。"
  },
  "delivery": {
    "mode": "announce",
    "to": "kimi-claw"
  }
}
EOF
)

echo "$PAYLOAD" | openclaw cron create --stdin
