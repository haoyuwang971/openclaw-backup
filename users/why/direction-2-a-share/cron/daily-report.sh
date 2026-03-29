#!/bin/bash
# A股投资组合每日报告生成脚本
# 运行时间: 工作日 15:35 (收盘后)

# 获取当前日期
DATE=$(date +%Y-%m-%d)
TIME=$(date +"%Y-%m-%d %H:%M:%S")

echo "[$TIME] 开始生成A股投资组合报告..."

# 股票代码列表
STOCKS_PRICE="300101.SZ,300769.SZ,600372.SH"
STOCKS_PRICE2="002407.SZ,002326.SZ"
STOCKS_TECH="300101.SZ,300769.SZ,600372.SH"
STOCKS_TECH2="002407.SZ,002326.SZ"

# 数据保存路径
DATA_DIR="/tmp/stock_data"
mkdir -p $DATA_DIR

# 获取实时价格数据
echo "[$TIME] 获取实时价格数据..."
# 价格数据 - 第一批
curl -s "https://ifind-api.example.com/realtime_price?ticker=${STOCKS_PRICE}&time=${TIME}" > ${DATA_DIR}/price_1_${DATE}.csv
# 价格数据 - 第二批  
curl -s "https://ifind-api.example.com/realtime_price?ticker=${STOCKS_PRICE2}&time=${TIME}" > ${DATA_DIR}/price_2_${DATE}.csv

# 获取技术指标数据
echo "[$TIME] 获取技术指标数据..."
# 技术指标 - 第一批
curl -s "https://ifind-api.example.com/realtime_tech?ticker=${STOCKS_TECH}&time=${TIME}" > ${DATA_DIR}/tech_1_${DATE}.csv
# 技术指标 - 第二批
curl -s "https://ifind-api.example.com/realtime_tech?ticker=${STOCKS_TECH2}&time=${TIME}" > ${DATA_DIR}/tech_2_${DATE}.csv

echo "[$TIME] 数据获取完成，等待分析报告生成..."
