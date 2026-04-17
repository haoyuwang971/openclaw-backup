# 06-Technical-Design.md - ROS2技术设计文档

> **文档版本**: 2.0  
> **最后更新**: 2026-04-13  
> **框架**: ROS2 Humble/Iron  
> **中间件**: DDS (默认 CycloneDDS)  
> **关联文档**: [01-PRD.md](./01-PRD.md), [02-Domain-Model.md](./02-Domain-Model.md), [04-State-Machine.md](./04-State-Machine.md), [05-Functional-Spec.md](./05-Functional-Spec.md)

---

## 版本变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| 2.0 | 2026-04-13 | **重构**: 基于ROS2框架重新设计，节点化架构，DDS通信 |
| 1.0 | 2026-04-13 | 初始版本 - 传统嵌入式架构 |

---

## 1. ROS2架构概述

### 1.1 架构设计原则

| 原则 | ROS2实现 | 说明 |
|------|----------|------|
| **节点解耦** | 独立进程/线程 | 每个功能模块一个Node，崩溃隔离 |
| **异步通信** | DDS Topics | Pub/Sub模式，解耦生产者和消费者 |
| **服务调用** | ROS2 Services | 同步请求-响应，用于配置和查询 |
| **长时间任务** | ROS2 Actions | 状态切换等异步可取消任务 |
| **参数管理** | Parameter Server | 运行时动态配置，持久化存储 |
| **实时性** | Multi-Threaded Executor | 实时节点优先级调度 |

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ROS2 DDS 域 (Domain ID: 42)                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        应用层节点                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  /ems/hmi   │  │/ems/north_io│  │    /ems/data_logger     │  │   │
│  │  │  (本地界面)  │  │  (北向MQTT)  │  │      (数据记录)          │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────────┘  │   │
│  │         │                │                    │                 │   │
│  │         ▼                ▼                    ▼                 │   │
│  │  Topics: /ems/system_state, /ems/alarms, /ems/metrics           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      核心业务节点层                              │   │
│  │                                                                 │   │
│  │   ┌─────────────────┐         ┌─────────────────┐              │   │
│  │   │ /ems/state_mgr  │◄───────►│ /ems/strategy   │              │   │
│  │   │   状态机管理     │  Action │   策略引擎       │              │   │
│  │   │   (生命周期)     │         │   (100ms周期)    │              │   │
│  │   └────────┬────────┘         └────────┬────────┘              │   │
│  │            │                           │                       │   │
│  │            ▼                           ▼                       │   │
│  │   ┌─────────────────┐         ┌─────────────────┐              │   │
│  │   │ /ems/security   │◄───────►│ /ems/dispatcher │              │   │
│  │   │   安全约束       │  Topic  │   控制分发       │              │   │
│  │   │   (实时节点)     │         │   (指令下发)     │              │   │
│  │   └─────────────────┘         └────────┬────────┘              │   │
│  │                                        │                       │   │
│  └────────────────────────────────────────┼───────────────────────┘   │
│                                           │                           │
│                                           ▼                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       南向通信节点层                             │   │
│  │                                                                 │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │   │
│  │  │/ems/pcs_driver│ │/ems/bms_driver│ │/ems/mppt_drv │            │   │
│  │  │  (PCS驱动)    │ │  (BMS驱动)    │ │ (MPPT驱动)   │            │   │
│  │  │  Modbus RTU   │ │  Modbus TCP   │ │  Modbus RTU  │            │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘            │   │
│  │                                                                 │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │   │
│  │  │/ems/sts_drv  │ │/ems/meter_drv│ │/ems/gen_drv  │            │   │
│  │  │  (STS驱动)    │ │  (电表驱动)   │ │  (柴发驱动)   │            │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘            │   │
│  │                                                                 │   │
│  │  Topic: /ems/device_data (聚合所有设备数据)                      │   │
│  │  Service: /ems/device_control (设备控制接口)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         物理设备层 (PCS/BMS/MPPT/STS/电表/柴发)
```

### 1.3 节点清单

| 节点名 | 命名空间 | 功能 | 实时性 | 优先级 |
|--------|----------|------|--------|--------|
| state_manager | /ems | 状态机核心 | Hard Realtime | 90 |
| security_engine | /ems | 安全约束检查 | Hard Realtime | 95 |
| strategy_engine | /ems | 策略计算 | Soft Realtime | 70 |
| control_dispatcher | /ems | 控制指令分发 | Hard Realtime | 85 |
| southbound_io | /ems | 南向设备聚合 | Firm Realtime | 80 |
| northbound_io | /ems | 北向MQTT | Best Effort | 50 |
| hmi | /ems | 本地界面 | Best Effort | 40 |
| data_logger | /ems | 数据记录 | Best Effort | 30 |

---

## 2. 接口定义 (Interfaces)

### 2.1 消息类型 (msg/)

#### SystemState.msg
```yaml
# 系统状态 - 状态机发布
uint8 state_id        # 0=Standby, 1=OffGrid, 2=CnetGrid, 3=CnetGent, 255=Fault
string state_name     # 状态名称
uint8 sub_state       # 子状态ID
float64 timestamp     # 时间戳 (ROS2 Time)

bool c1_ready         # 条件标志
bool c2_fault
bool c3_grid_ready
bool c4_gen_ready
bool c5_off_grid
bool c6_standby

uint8[] active_faults # 活跃故障码列表
```

#### DeviceData.msg
```yaml
# 设备数据聚合 - 南向节点发布
std_msgs/Header header  # stamp: 采集时间, frame_id: "ems_device_data"

# PCS数据 (5台)
PCSData[] pcs_array     # 长度5

# BMS数据 (4组DC柜)
BMSData[] bms_array     # 长度4

# MPPT数据 (7路)
MPPTData[] mppt_array   # 长度7

# 电表数据
MeterData meter_grid    # 关口表
MeterData meter_storage # 储能表
MeterData meter_load    # 负载表
MeterData meter_gen     # 柴发表

# 开关状态
uint8 sts_status        # STS状态 0=分闸, 1=合闸
uint8 ats_status        # ATS状态 0=离线, 1=市电, 2=柴发

# 柴发状态
bool gen_running
bool gen_breaker_closed
bool gen_ready
```

#### PCSData.msg
```yaml
uint8 id              # PCS编号 1-5
float32 ac_power      # 交流有功功率 [kW], 正=放电
float32 dc_voltage    # 直流母线电压 [V]
float32 dc_current    # 直流电流 [A]
uint16 status_word    # 状态字
uint16 fault_word     # 故障字
uint8 run_mode        # 0=待机, 1=PQ, 2=VF
bool online           # 通信状态
```

#### BMSData.msg
```yaml
uint8 id              # DC柜编号 1-4
float32 soc           # SOC [%]
float32 soh           # SOH [%]
float32 voltage       # 总电压 [V]
float32 current       # 总电流 [A], 正=充电
float32 max_temp      # 最高温度 [°C]
uint16 status_word
uint16 fault_word
bool online
```

#### MPPTData.msg
```yaml
uint8 id              # MPPT编号 1-7
float32 pv_power      # 光伏功率 [kW]
float32 pv_voltage    # PV电压 [V]
float32 pv_current    # PV电流 [A]
float32 limit_power   # 当前限功率值 [kW]
uint16 status_word
bool online
```

#### MeterData.msg
```yaml
string type           # "grid"/"storage"/"load"/"gen"
float32 power         # 有功功率 [kW]
float32 voltage_a     # A相电压 [V]
float32 current_a     # A相电流 [A]
float32 frequency     # 频率 [Hz]
```

#### StrategyOutput.msg
```yaml
# 策略引擎输出
float32 target_pcs_clu1   # 簇1目标PCS功率 [kW]
float32 target_pcs_clu2   # 簇2目标PCS功率 [kW]
float32 pv_limit_clu1     # 簇1光伏限功率 [kW]
float32 pv_limit_clu2     # 簇2光伏限功率 [kW]
bool gen_start_request    # 柴发启动请求
uint8 strategy_zone       # 当前SOC区间
```

#### ControlCommand.msg
```yaml
# 控制指令 - 分发器发布到南向节点
std_msgs/Header header

# PCS功率设定值 (5台)
float32[] pcs_power_set   # 长度5, [kW]

# MPPT限功率 (7路)
float32[] mppt_limit_set  # 长度7, [kW]

# 柴发控制
bool gen_start            # 启停信号

# 来源
string source             # "strategy"/"manual"/"emergency"
uint8 priority            # 0-255, 数字越大优先级越高
```

#### SecurityConstraint.msg
```yaml
# 安全约束触发告警
uint8 constraint_type     # 0=防逆流, 1=需量, 2=SOC上限, 3=SOC下限, 4=变化率
float32 original_value    # 原始值
float32 constrained_value # 约束后值
float32 limit_value       # 限制值
string description
```

### 2.2 服务类型 (srv/)

#### SetMode.srv
```yaml
# 请求
uint8 mode              # 0=手动, 1=自动
float32 manual_pcs1     # 手动模式PCS1功率 (mode=0时有效)
float32 manual_pcs2     # 手动模式PCS2功率
---
# 响应
bool success
string message
```

#### GetStatus.srv
```yaml
# 请求
bool include_history    # 是否包含历史数据
---
# 响应
SystemState state
DeviceData device_data
StrategyOutput strategy
string[] recent_alarms
```

#### DeviceControl.srv
```yaml
# 设备控制接口
string device_type      # "pcs"/"mppt"/"gen"
uint8 device_id
string command          # "start"/"stop"/"set_power"/"set_limit"
float32 value           # 设定值
---
bool success
string message
float32 actual_value    # 实际执行值
```

#### SetParameter.srv
```yaml
# 参数配置
string param_name
float64 param_value
bool persistent         # 是否持久化
---
bool success
string message
float64 old_value
```

### 2.3 动作类型 (action/)

#### StateTransition.action
```yaml
# 目标
uint8 target_state      # 目标状态ID
---
# 结果
bool success
uint8 final_state
string message
float64 transition_time # 切换耗时 [s]
---
# 反馈
uint8 current_step      # 当前步骤
string step_description
float64 progress        # 0.0-1.0
```

#### GeneratorStart.action
```yaml
# 目标
bool start              # true=启动, false=停止
float32 timeout         # 超时时间 [s]
---
# 结果
bool success
string message
float64 actual_time
---
# 反馈
uint8 phase             # 0=信号发出, 1=启动中, 2=稳定运行
float32 gen_voltage
float32 gen_frequency
```

---

## 3. 节点详细设计

### 3.1 /ems/state_manager (状态机节点)

#### 节点职责
- 维护系统状态机 (SysStandby → SysOffGrid → SysCnetGrid → SysCnetGent → SysFault)
- 周期扫描状态转换条件 (100ms)
- 提供状态切换Action接口
- 管理状态进入/退出回调

#### 类设计
```python
# Python示例 (也可用C++)
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from ems_msgs.msg import SystemState, DeviceData
from ems_msgs.action import StateTransition

class StateManager(Node):
    def __init__(self):
        super().__init__('state_manager', namespace='ems')
        
        # 参数声明
        self.declare_parameter('scan_period_ms', 100)
        self.declare_parameter('debounce_cycles', 3)
        
        # Publisher - 发布系统状态
        self.state_pub = self.create_publisher(
            SystemState, 'system_state', 10)
        
        # Subscriber - 订阅设备数据
        self.device_sub = self.create_subscription(
            DeviceData, 'device_data', self.on_device_data, 10)
        
        # Action Server - 状态切换请求
        self.transition_server = ActionServer(
            self, StateTransition, 'state_transition', 
            self.execute_transition)
        
        # Timer - 状态机扫描 (100ms)
        period = self.get_parameter('scan_period_ms').value / 1000.0
        self.timer = self.create_timer(period, self.state_machine_loop)
        
        # 状态变量
        self.current_state = State.STANDBY
        self.debounce_counter = 0
        self.device_data = None
        
    def state_machine_loop(self):
        """状态机主循环 - 每100ms执行"""
        # 1. 更新条件检测
        conditions = self.evaluate_conditions()
        
        # 2. 检查状态转换
        next_state = self.check_transition(conditions)
        
        if next_state != self.current_state:
            if self.debounce_counter < self.get_parameter('debounce_cycles').value:
                self.debounce_counter += 1
            else:
                self.perform_transition(next_state)
        else:
            self.debounce_counter = 0
            
        # 3. 发布当前状态
        self.publish_state()
        
    def evaluate_conditions(self):
        """评估C1-C6条件"""
        if self.device_data is None:
            return Conditions()
            
        c = Conditions()
        # C1: 开机就绪
        c.c1_ready = (all_comm_ok(self.device_data) and 
                     all_no_fault(self.device_data) and
                     pcs_config_ok(self.device_data))
        
        # C2: 故障条件
        c.c2_fault = (any_comm_fail(self.device_data) or 
                     any_device_fault(self.device_data))
        
        # C3-C6: 其他条件...
        return c
        
    def perform_transition(self, target_state):
        """执行状态转换"""
        self.get_logger().info(f'Transition: {self.current_state} -> {target_state}')
        
        # 退出当前状态
        self.on_state_exit(self.current_state)
        
        # 状态切换
        self.current_state = target_state
        
        # 进入新状态
        self.on_state_enter(target_state)
        
    def on_state_enter(self, state):
        """状态进入回调"""
        if state == State.OFFGRID:
            # 离网状态: 启动VF模式
            self.start_vf_mode()
        elif state == State.CNETGRID:
            # 并网状态: 启动PQ模式
            self.start_pq_mode()
            
    def execute_transition(self, goal_handle):
        """Action: 执行状态切换 (外部请求)"""
        target = goal_handle.request.target_state
        
        # 执行切换流程
        feedback = StateTransition.Feedback()
        
        steps = self.get_transition_steps(self.current_state, target)
        for i, step in enumerate(steps):
            feedback.current_step = i
            feedback.step_description = step['desc']
            feedback.progress = i / len(steps)
            goal_handle.publish_feedback(feedback)
            
            # 执行步骤
            result = self.execute_step(step)
            if not result:
                goal_handle.abort()
                return StateTransition.Result(success=False)
                
        goal_handle.succeed()
        return StateTransition.Result(success=True, final_state=target)
```

#### 配置参数 (params/state_manager.yaml)
```yaml
state_manager:
  ros__parameters:
    scan_period_ms: 100
    debounce_cycles: 3
    
    # 状态超时配置
    transition_timeout:
      standby_to_offgrid: 10.0    # s
      offgrid_to_cnetgrid: 5.0    # s
      cnetgrid_to_offgrid: 2.0    # s
      
    # 同步条件阈值
    sync_threshold:
      volt_diff_percent: 5.0      # %
      freq_diff_hz: 0.5           # Hz
      phase_diff_deg: 10.0        # °
```

### 3.2 /ems/strategy_engine (策略引擎节点)

#### 节点职责
- 周期执行策略计算 (100ms，与状态机同步)
- 实现四层SOC阈值策略
- 三场景适配 (并网/离网/并柴发)
- 簇间SOC均衡

#### 类设计
```python
class StrategyEngine(Node):
    def __init__(self):
        super().__init__('strategy_engine', namespace='ems')
        
        # Subscribers
        self.state_sub = self.create_subscription(
            SystemState, 'system_state', self.on_state, 10)
        self.device_sub = self.create_subscription(
            DeviceData, 'device_data', self.on_device_data, 10)
        
        # Publisher
        self.strategy_pub = self.create_publisher(
            StrategyOutput, 'strategy_output', 10)
        
        # Timer (100ms)
        self.timer = self.create_timer(0.1, self.calculate_strategy)
        
        # 当前状态缓存
        self.current_state = None
        self.device_data = None
        self.last_strategy = None
        
        # 参数
        self.declare_parameter('green_threshold', 90.0)
        self.declare_parameter('green_hysteresis', 2.0)
        self.declare_parameter('backup_threshold', 70.0)
        self.declare_parameter('backup_hysteresis', 1.0)
        self.declare_parameter('gen_start_soc', 20.0)
        self.declare_parameter('anti_reverse_margin', 5.0)
        
    def calculate_strategy(self):
        """策略计算主函数"""
        if self.device_data is None or self.current_state is None:
            return
            
        # 获取输入
        soc1 = self.get_cluster1_soc()
        soc2 = self.get_cluster2_soc()
        min_soc = min(soc1, soc2)
        
        # 确定SOC区间
        zone = self.determine_soc_zone(min_soc)
        
        # 根据状态选择策略
        state_id = self.current_state.state_id
        
        if state_id == SystemState.SYS_OFFGRID:
            output = self.calc_offgrid_strategy(zone, soc1, soc2)
        elif state_id == SystemState.SYS_CNETGRID:
            output = self.calc_cnetgrid_strategy(zone, soc1, soc2)
        elif state_id == SystemState.SYS_CNETGENT:
            output = self.calc_cnetgent_strategy(zone, soc1, soc2)
        else:
            output = StrategyOutput()  # 其他状态无输出
            
        # 簇间均衡
        output = self.balance_clusters(output, soc1, soc2)
        
        # 发布策略
        self.strategy_pub.publish(output)
        self.last_strategy = output
        
    def determine_soc_zone(self, soc):
        """确定SOC区间"""
        green_on = (self.get_parameter('green_threshold').value + 
                   self.get_parameter('green_hysteresis').value) / 100.0
        green_off = (self.get_parameter('green_threshold').value - 
                    self.get_parameter('green_hysteresis').value) / 100.0
        backup_on = (self.get_parameter('backup_threshold').value - 
                    self.get_parameter('backup_hysteresis').value) / 100.0
        backup_off = (self.get_parameter('backup_threshold').value + 
                     self.get_parameter('backup_hysteresis').value) / 100.0
        gen_start = self.get_parameter('gen_start_soc').value / 100.0
        
        if soc >= green_on:
            return StrategyZone.ZONE_GREEN
        elif soc >= backup_off:
            return StrategyZone.ZONE_BACKUP_OFF
        elif soc >= backup_on:
            return StrategyZone.ZONE_BACKUP_HYST
        elif soc >= gen_start:
            return StrategyZone.ZONE_BACKUP_ON
        else:
            return StrategyZone.ZONE_GEN_FORCE
            
    def calc_offgrid_strategy(self, zone, soc1, soc2):
        """离网策略"""
        output = StrategyOutput()
        load = self.get_load_power()
        gen_running = self.device_data.gen_running
        
        if zone == StrategyZone.ZONE_GREEN:
            # ≥92%: 满功率放电
            output.target_pcs_clu1 = load * 0.5
            output.target_pcs_clu2 = load * 0.5
            output.gen_start_request = False
            
        elif zone == StrategyZone.ZONE_BACKUP_OFF:
            # 71%-92%: 维持供电
            output.target_pcs_clu1 = load * 0.5
            output.target_pcs_clu2 = load * 0.5
            output.gen_start_request = False
            
        elif zone == StrategyZone.ZONE_BACKUP_HYST:
            # 滞环区: 保持上一周期
            if self.last_strategy:
                output.target_pcs_clu1 = self.last_strategy.target_pcs_clu1
                output.target_pcs_clu2 = self.last_strategy.target_pcs_clu2
            output.gen_start_request = False
            
        elif zone == StrategyZone.ZONE_BACKUP_ON:
            # 20%-69%: 降载5%，准备启柴发
            output.target_pcs_clu1 = load * 0.475
            output.target_pcs_clu2 = load * 0.475
            output.gen_start_request = not gen_running
            
        else:  # ZONE_GEN_FORCE
            # <20%: 柴发强制
            if gen_running:
                output.target_pcs_clu1 = 0.0
                output.target_pcs_clu2 = 0.0
            else:
                output.target_pcs_clu1 = load * 0.5
                output.target_pcs_clu2 = load * 0.5
                output.gen_start_request = True
                
        output.strategy_zone = zone
        return output
        
    def calc_cnetgrid_strategy(self, zone, soc1, soc2):
        """并网策略"""
        output = StrategyOutput()
        load = self.get_load_power()
        margin = self.get_parameter('anti_reverse_margin').value
        
        if zone == StrategyZone.ZONE_GREEN:
            # ≥92%: 负载跟随，留5%防逆流余量
            output.target_pcs_clu1 = load * 0.475
            output.target_pcs_clu2 = load * 0.475
            
        elif zone == StrategyZone.ZONE_BACKUP_OFF:
            # 71%-92%: PCS待机，光伏直充
            output.target_pcs_clu1 = 0.0
            output.target_pcs_clu2 = 0.0
            
        else:  # <69%: 市电充电
            charge_need = self.calc_charge_need(soc1, soc2)
            demand_limit = self.get_demand_limit()
            max_charge = demand_limit - load - margin
            actual_charge = min(charge_need, max_charge)
            output.target_pcs_clu1 = -actual_charge * 0.5
            output.target_pcs_clu2 = -actual_charge * 0.5
            
        output.gen_start_request = False
        output.strategy_zone = zone
        return output
        
    def balance_clusters(self, output, soc1, soc2):
        """簇间SOC均衡"""
        soc_diff = soc1 - soc2
        total = output.target_pcs_clu1 + output.target_pcs_clu2
        
        if abs(soc_diff) > 0.05:  # 差异>5%
            factor = max(-0.2, min(0.2, soc_diff * 0.5))
            
            if total > 0:  # 放电
                output.target_pcs_clu1 = total * (0.5 + factor)
                output.target_pcs_clu2 = total * (0.5 - factor)
            else:  # 充电
                output.target_pcs_clu1 = total * (0.5 - factor)
                output.target_pcs_clu2 = total * (0.5 + factor)
                
        return output
```

### 3.3 /ems/security_engine (安全约束节点)

#### 节点职责
- 实时约束检查 (Hard Realtime)
- 防逆流、需量、SOC边界、变化率限制
- 光伏限发计算
- 告警发布

#### 类设计
```python
class SecurityEngine(Node):
    def __init__(self):
        super().__init__('security_engine', namespace='ems')
        
        # 使用MultiThreadedExecutor的Realtime Callback Group
        self.realtime_cb_group = MutuallyExclusiveCallbackGroup()
        
        self.strategy_sub = self.create_subscription(
            StrategyOutput, 'strategy_output', 
            self.on_strategy, 10, callback_group=self.realtime_cb_group)
        
        self.device_sub = self.create_subscription(
            DeviceData, 'device_data',
            self.on_device_data, 10, callback_group=self.realtime_cb_group)
        
        self.constraint_pub = self.create_publisher(
            SecurityConstraint, 'security_constraint', 10)
        
        self.control_pub = self.create_publisher(
            ControlCommand, 'control_cmd', 10)
        
        # 100ms实时循环
        self.timer = self.create_timer(
            0.1, self.security_check, 
            callback_group=self.realtime_cb_group)
        
        self.current_strategy = None
        self.device_data = None
        self.last_pcs_power = [0.0, 0.0]
        
    def security_check(self):
        """安全约束检查 - 硬实时"""
        if self.current_strategy is None or self.device_data is None:
            return
            
        pcs1 = self.current_strategy.target_pcs_clu1
        pcs2 = self.current_strategy.target_pcs_clu2
        
        # 应用约束
        pcs1, pcs2 = self.apply_anti_reverse(pcs1, pcs2)
        pcs1, pcs2 = self.apply_demand_constraint(pcs1, pcs2)
        pcs1, pcs2 = self.apply_soc_boundary(pcs1, pcs2)
        pcs1, pcs2 = self.apply_ramp_rate(pcs1, pcs2)
        
        pv_limit1, pv_limit2 = self.apply_pv_limit()
        
        # 构建控制指令
        cmd = ControlCommand()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = "security_engine"
        
        # 分配到5台PCS
        cmd.pcs_power_set = [pcs1/3, pcs1/3, pcs1/3, pcs2/2, pcs2/2]
        
        # 分配到7路MPPT
        cmd.mppt_limit_set = [
            pv_limit1/4, pv_limit1/4, pv_limit1/4, pv_limit1/4,
            pv_limit2/3, pv_limit2/3, pv_limit2/3
        ]
        
        cmd.gen_start = self.current_strategy.gen_start_request
        cmd.source = "security_engine"
        cmd.priority = 200  # 高优先级
        
        self.control_pub.publish(cmd)
        
        # 更新记录
        self.last_pcs_power = [pcs1, pcs2]
        
    def apply_anti_reverse(self, pcs1, pcs2):
        """防逆流约束"""
        margin = 5.0  # kW
        load = self.device_data.meter_load.power
        total = pcs1 + pcs2
        
        if total > 0:  # 放电状态
            max_discharge = load - margin
            if total > max_discharge:
                scale = max_discharge / total if total > 0 else 0
                pcs1 *= scale
                pcs2 *= scale
                self.publish_constraint_alert("anti_reverse", total, max_discharge)
                
        return pcs1, pcs2
        
    def apply_demand_constraint(self, pcs1, pcs2):
        """需量约束"""
        demand_limit = 500.0  # kW
        load = self.device_data.meter_load.power
        
        total_load = load + max(0, -pcs1) + max(0, -pcs2)
        
        if total_load > demand_limit:
            excess = total_load - demand_limit
            if pcs1 < 0:
                pcs1 = min(0, pcs1 + excess/2)
            if pcs2 < 0:
                pcs2 = min(0, pcs2 + excess/2)
            self.publish_constraint_alert("demand", total_load, demand_limit)
            
        return pcs1, pcs2
        
    def apply_soc_boundary(self, pcs1, pcs2):
        """SOC边界约束"""
        soc_max = 0.95
        soc_min = 0.20
        
        soc1 = self.device_data.bms_array[0].soc / 100.0
        soc2 = self.device_data.bms_array[2].soc / 100.0
        
        # 簇1
        if soc1 >= soc_max and pcs1 < 0:
            pcs1 = 0
            self.publish_constraint_alert("soc_max", soc1, soc_max)
        if soc1 <= soc_min and pcs1 > 0:
            pcs1 = 0
            self.publish_constraint_alert("soc_min", soc1, soc_min)
            
        # 簇2
        if soc2 >= soc_max and pcs2 < 0:
            pcs2 = 0
        if soc2 <= soc_min and pcs2 > 0:
            pcs2 = 0
            
        return pcs1, pcs2
        
    def apply_ramp_rate(self, pcs1, pcs2):
        """功率变化率约束"""
        ramp_limit = 50.0 * 0.1  # 50kW/s * 0.1s = 5kW/周期
        
        delta1 = pcs1 - self.last_pcs_power[0]
        if abs(delta1) > ramp_limit:
            sign = 1 if delta1 > 0 else -1
            pcs1 = self.last_pcs_power[0] + sign * ramp_limit
            
        delta2 = pcs2 - self.last_pcs_power[1]
        if abs(delta2) > ramp_limit:
            sign = 1 if delta2 > 0 else -1
            pcs2 = self.last_pcs_power[1] + sign * ramp_limit
            
        return pcs1, pcs2
        
    def apply_pv_limit(self):
        """光伏限发约束"""
        soc1 = self.device_data.bms_array[0].soc / 100.0
        soc2 = self.device_data.bms_array[2].soc / 100.0
        
        pv_limit1 = 9999.0
        pv_limit2 = 9999.0
        
        if soc1 > 0.90:
            factor = max(0, (0.95 - soc1) / 0.05)
            allow_charge = 260 * factor
            pcs1 = self.current_strategy.target_pcs_clu1 if self.current_strategy else 0
            pv_limit1 = max(0, allow_charge + pcs1 / 0.98)
            
        if soc2 > 0.90:
            factor = max(0, (0.95 - soc2) / 0.05)
            allow_charge = 260 * factor
            pcs2 = self.current_strategy.target_pcs_clu2 if self.current_strategy else 0
            pv_limit2 = max(0, allow_charge + pcs2 / 0.98)
            
        return pv_limit1, pv_limit2
```

### 3.4 /ems/southbound_io (南向通信节点)

#### 节点职责
- 聚合所有南向设备通信
- Modbus RTU/TCP 设备驱动
- 硬线DI/DO控制
- 发布统一的DeviceData话题
- 提供设备控制Service

#### 类设计
```python
class SouthboundIO(Node):
    def __init__(self):
        super().__init__('southbound_io', namespace='ems')
        
        # Publishers
        self.device_pub = self.create_publisher(
            DeviceData, 'device_data', 10)
        
        # Service
        self.control_srv = self.create_service(
            DeviceControl, 'device_control', self.handle_device_control)
        
        # 设备驱动实例
        self.pcs_drivers = [PCSDriver(i+1) for i in range(5)]
        self.bms_drivers = [BMSDriver(1, "LAN1"), BMSDriver(2, "LAN2")]
        self.mppt_drivers = [MPPTDriver(i+1) for i in range(7)]
        self.sts_driver = STSDriver()
        self.meter_driver = MeterDriver()
        self.gen_driver = GeneratorDriver()
        
        # 定时器 - 不同周期
        self.create_timer(0.1, self.read_sts)      # STS 100ms
        self.create_timer(0.3, self.read_pcs)      # PCS 300ms
        self.create_timer(1.0, self.read_meters)   # 电表 1s
        self.create_timer(2.0, self.read_mppt)     # MPPT 2s
        self.create_timer(3.0, self.read_bms)      # BMS 3s
        
        # 数据缓存
        self.device_data = DeviceData()
        self.device_data.header.frame_id = "ems_device_data"
        
    def read_pcs(self):
        """读取PCS数据"""
        for i, driver in enumerate(self.pcs_drivers):
            try:
                data = driver.read()
                self.device_data.pcs_array[i] = data
            except Exception as e:
                self.device_data.pcs_array[i].online = False
                self.get_logger().warn(f'PCS {i+1} read failed: {e}')
                
    def read_bms(self):
        """读取BMS数据"""
        for i, driver in enumerate(self.bms_drivers):
            try:
                data = driver.read()
                # 每个BAM管理2个DC柜
                self.device_data.bms_array[i*2] = data[0]
                self.device_data.bms_array[i*2+1] = data[1]
            except Exception as e:
                self.device_data.bms_array[i*2].online = False
                self.device_data.bms_array[i*2+1].online = False
                
    def read_sts(self):
        """读取STS和发布设备数据"""
        try:
            sts_data = self.sts_driver.read()
            self.device_data.sts_status = sts_data.sts_status
            self.device_data.ats_status = sts_data.ats_status
        except:
            pass
            
        # 更新时间戳并发布
        self.device_data.header.stamp = self.get_clock().now().to_msg()
        self.device_pub.publish(self.device_data)
        
    def handle_device_control(self, request, response):
        """处理设备控制请求"""
        try:
            if request.device_type == "pcs":
                driver = self.pcs_drivers[request.device_id - 1]
                if request.command == "set_power":
                    driver.set_power(request.value)
                    response.actual_value = request.value
                    
            elif request.device_type == "mppt":
                driver = self.mppt_drivers[request.device_id - 1]
                if request.command == "set_limit":
                    driver.set_limit(request.value)
                    
            elif request.device_type == "gen":
                if request.command == "start":
                    self.gen_driver.start()
                else:
                    self.gen_driver.stop()
                    
            response.success = True
            response.message = "OK"
            
        except Exception as e:
            response.success = False
            response.message = str(e)
            
        return response
```

### 3.5 其他节点

#### /ems/northbound_io (北向通信)
- MQTT客户端，连接云平台
- 订阅本地话题，上报云端
- 接收云端指令，下发本地

#### /ems/hmi (本地界面)
- 本地触摸屏界面
- 状态显示、手动控制
- 参数配置界面

#### /ems/data_logger (数据记录)
- 订阅所有话题，记录到本地数据库
- 断点续传支持
- 日志轮转管理

---

## 4. 启动与配置

### 4.1 Launch文件

```python
# launch/ems_bringup.py
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('domain_id', default_value='42'),
        
        # 南向通信节点 (最高优先级)
        Node(
            package='ems_driver',
            executable='southbound_io',
            name='southbound_io',
            namespace='ems',
            parameters=['config/southbound.yaml'],
            priority=90,
            respawn=True
        ),
        
        # 安全约束节点 (硬实时)
        Node(
            package='ems_core',
            executable='security_engine',
            name='security_engine',
            namespace='ems',
            parameters=['config/security.yaml'],
            priority=95,
            respawn=True
        ),
        
        # 状态机节点
        Node(
            package='ems_core',
            executable='state_manager',
            name='state_manager',
            namespace='ems',
            parameters=['config/state_manager.yaml'],
            priority=90,
            respawn=True
        ),
        
        # 策略引擎节点
        Node(
            package='ems_core',
            executable='strategy_engine',
            name='strategy_engine',
            namespace='ems',
            parameters=['config/strategy.yaml'],
            priority=70
        ),
        
        # 北向通信
        Node(
            package='ems_cloud',
            executable='northbound_io',
            name='northbound_io',
            namespace='ems',
            parameters=['config/cloud.yaml'],
            priority=50
        ),
        
        # HMI
        Node(
            package='ems_hmi',
            executable='hmi_node',
            name='hmi',
            namespace='ems',
            priority=40
        ),
        
        # 数据记录
        Node(
            package='ems_recorder',
            executable='data_logger',
            name='data_logger',
            namespace='ems',
            parameters=['config/recorder.yaml'],
            priority=30
        ),
    ])
```

### 4.2 DDS配置 (cyclonedds.xml)

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS>
  <Domain id="42">
    <General>
      <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
      <AllowMulticast>true</AllowMulticast>
      <MaxMessageSize>65500B</MaxMessageSize>
    </General>
    
    <Internal>
      <SocketReceiveBufferSize>10MB</SocketReceiveBufferSize>
      <SocketSendBufferSize>10MB</SocketSendBufferSize>
    </Internal>
    
    <!-- QoS for Realtime Topics -->
    <Topic name="ems/control_cmd">
      <QoS>
        <Reliability>RELIABLE</Reliability>
        <Durability>VOLATILE</Durability>
        <Deadline period="100ms"/>
        <LatencyBudget duration="10ms"/>
      </QoS>
    </Topic>
    
    <Topic name="ems/device_data">
      <QoS>
        <Reliability>BEST_EFFORT</Reliability>
        <Durability>VOLATILE</Durability>
        <Deadline period="100ms"/>
      </QoS>
    </Topic>
  </Domain>
</CycloneDDS>
```

---

## 5. 实时性保障

### 5.1 实时性等级

| 等级 | 节点 | 周期 | 容忍延迟 |
|------|------|------|----------|
| Hard Realtime | security_engine | 100ms | <5ms |
| Hard Realtime | state_manager | 100ms | <10ms |
| Firm Realtime | southbound_io | 混合 | <50ms |
| Soft Realtime | strategy_engine | 100ms | <100ms |
| Best Effort | northbound_io | 1s | 无要求 |

### 5.2 Linux实时配置

```bash
# 启用PREEMPT_RT内核
# CPU隔离
echo 2,3 > /sys/devices/system/cpu/isolated

# 设置节点CPU亲和性
chrt -f 90 taskset -c 2 ros2 run ems_core security_engine
chrt -f 90 taskset -c 3 ros2 run ems_core state_manager
```

---

## 6. 调试工具

### 6.1 命令行工具

```bash
# 查看系统状态
ros2 topic echo /ems/system_state

# 查看设备数据
ros2 topic echo /ems/device_data

# 手动发送控制指令
ros2 topic pub /ems/control_cmd ems_msgs/ControlCommand \
  '{pcs_power_set: [10.0, 10.0, 10.0, 0.0, 0.0], source: "manual", priority: 255}'

# 调用服务查询状态
ros2 service call /ems/get_status ems_msgs/GetStatus '{}'

# 触发状态切换
ros2 action send_goal /ems/state_transition ems_msgs/StateTransition \
  '{target_state: 2}'

# 查看节点图
ros2 run rqt_graph rqt_graph

# 查看话题频率
ros2 topic hz /ems/device_data
```

### 6.2 日志系统

```python
# 分级日志
self.get_logger().debug("调试信息")
self.get_logger().info("普通信息")
self.get_logger().warn("警告")
self.get_logger().error("错误")

# 查看日志
ros2 topic echo /rosout
journalctl -u ems -f
```

---

## 7. 测试

### 7.1 单元测试

```python
# test/test_strategy_engine.py
import pytest
from ems_core.strategy_engine import StrategyEngine

def test_soc_zone_determination():
    engine = StrategyEngine()
    
    assert engine.determine_soc_zone(0.95) == StrategyZone.ZONE_GREEN
    assert engine.determine_soc_zone(0.92) == StrategyZone.ZONE_GREEN
    assert engine.determine_soc_zone(0.88) == StrategyZone.ZONE_BACKUP_OFF
    assert engine.determine_soc_zone(0.20) == StrategyZone.ZONE_BACKUP_ON
    assert engine.determine_soc_zone(0.15) == StrategyZone.ZONE_GEN_FORCE

def test_offgrid_strategy_green_zone():
    engine = StrategyEngine()
    # ... 测试代码
```

### 7.2 集成测试

```bash
# 启动测试环境
ros2 launch ems_bringup ems_test.launch.py

# 模拟设备数据发布
ros2 topic pub /ems/device_data ems_msgs/DeviceData ...

# 验证状态转换
ros2 action send_goal /ems/state_transition ...
```

---

## 8. 附录

### 8.1 工作空间结构

```
~/ems_ws/
├── src/
│   ├── ems_msgs/          # 自定义消息/服务/动作
│   │   ├── msg/
│   │   ├── srv/
│   │   └── action/
│   ├── ems_core/          # 核心节点 (状态机/策略/安全)
│   ├── ems_driver/        # 南向驱动节点
│   ├── ems_cloud/         # 北向云节点
│   ├── ems_hmi/           # 本地界面
│   └── ems_recorder/      # 数据记录
├── config/                # 配置文件
│   ├── state_manager.yaml
│   ├── strategy.yaml
│   └── security.yaml
├── launch/
│   └── ems_bringup.py
└── test/                  # 测试代码
```

### 8.2 构建命令

```bash
cd ~/ems_ws
colcon build --packages-select ems_msgs
source install/setup.bash
colcon build
```

### 8.3 参考文档

- [05-Functional-Spec.md](./05-Functional-Spec.md): 功能规格说明书
- [ROS2 Documentation](https://docs.ros.org/en/humble/)
- [ROS2 Realtime](https://ros-realtime.github.io/)
- [CycloneDDS](https://cyclonedds.io/)
