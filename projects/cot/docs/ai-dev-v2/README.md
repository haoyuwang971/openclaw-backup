# ai-dev v2.0 - 基于规范重新梳理

**状态**: 进行中 — 基于新版文档规范重新梳理 ai-dev 全系列文档

## 规范依据
规范文件存放于 `users/why/direction-1-ems/standards/`，按 **EMS / BMS / PCS / 微网 / 储能通用与并网** 五大类组织。

## 已完成文档

| # | 文档 | 版本 | 核心变化 |
|---|------|------|----------|
| 00 | [00-Context-v2.md](./00-Context-v2.md) | v2.0 | 新增国标依据章节（10份标准）；拓扑术语标准化；涉网性能指标具体化；约束条件与国标对齐 |
| 01 | [01-PRD-v2.md](./01-PRD-v2.md) | v2.0 | 每FR条目标注来源标准；新增涉网保护章节（LVRT/HVRT/保护定值）；性能指标引用国标数值；故障分级与国标对齐；新增国标引用速查表 |

## 待办
- [x] 00-Context-v2.md
- [x] 01-PRD-v2.md
- [ ] 02-Domain-Model-v2.md
- [ ] 03-Architecture-v2.md
- [ ] 04-State-Machine-v2.md
- [ ] 05-Functional-Spec-v2.md
- [ ] 06-Technical-Design-v2.md
- [ ] 07-API-Contract-v2.yml
- [ ] 08-Test-Spec-v2.md
- [ ] 09-Task-Breakdown-v2.json
- [ ] 10-Frontend-Backend-v2.md
- [ ] HMI-Design-v2.md

## 规范增强核心原则
1. **每处技术参数必有国标来源** — 功率响应时间、切换时间、保护定值等均引用GB/T具体条款
2. **术语标准化** — PQ/VF/LVRT/HVRT/DI/DO等术语增加国标全称对照
3. **涉网性能新增** — GB/T 36547要求的低电压穿越、高电压穿越、涉网保护定值纳入Must Have
4. **故障分级对齐** — 从原四级调整为与GB/T 42726三级+设备级保护四级混合体系
5. **通信协议明确** — Modbus/DLT645/MQTT均标注国标条款依据
