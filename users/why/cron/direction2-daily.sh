#!/bin/bash
# why用户 - 方向2：A股投资 - 每日收盘复盘

# 执行时间：每日 15:30
# 内容：大盘复盘、持仓诊断、技术分析

cd /root/.openclaw/workspace

# 加载持仓和自选股
PORTFOLIO=$(cat users/why/direction-2-a-share/portfolio.json)
WATCHLIST=$(cat users/why/direction-2-a-share/watchlist.json)

PAYLOAD=$(cat <<EOF
{
  "cron": "30 15 * * *",
  "name": "why-direction2-a-share-daily",
  "description": "why用户-方向2：A股每日收盘复盘",
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "content": "用户why的方向2（A股投资）每日收盘复盘任务。请执行：1）大盘复盘（上证指数、深证成指、创业板指走势）2）持仓诊断（根据 portfolio.json 分析持仓个股表现）3）自选股跟踪（根据 watchlist.json）4）技术指标汇总（MA/MACD/KDJ/RSI）。整理成复盘报告，保存到 users/why/direction-2-a-share/daily/ 目录，文件命名格式：YYYY-MM-DD-daily-review.md。注意用户2021年入市，历史有亏损，风格需谨慎。"
  },
  "delivery": {
    "mode": "announce",
    "to": "kimi-claw"
  }
}
EOF
)

echo "$PAYLOAD" | openclaw cron create --stdin
