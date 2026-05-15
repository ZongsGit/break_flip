# 惯性突破（Break-Flip）量化信号检测系统

> 基于日K线数据，将「惯性突破（标准图）」交易形态从主观视觉信号转化为可量化执行的趋势交易信号。
> 提供命令行 (matplotlib) 与 Web (Flask + ECharts) 两种使用方式。

---

## 📋 目录

- [项目特性](#项目特性)
- [项目结构](#项目结构)
- [核心算法思路](#核心算法思路)
- [安装与启动](#安装与启动)
- [使用指引](#使用指引)
- [策略参数说明](#策略参数说明)
- [数据格式](#数据格式)
- [常见问题](#常见问题)

---

## 项目特性

- ✅ **严格量化的五步检测逻辑**：支撑边界 → 假跌破 → 停顿减速 → 站回 → 量能验证
- ✅ **CONFIG 集中管理**：所有策略参数可一键调整，便于回测对比
- ✅ **双模式输出**：命令行 (matplotlib) + Web 应用 (Flask + ECharts 交互图表)
- ✅ **支持自定义数据**：在 Web 端可上传任意 CSV 文件
- ✅ **结果可导出**：信号表一键导出为 CSV
- ✅ **中文标签 + 日志**：参数可视化、信号详情逐条打印

---

## 项目结构

~~~
break_flip/
├── analysis.py              # 核心分析模块（数据加载 + 信号检测，命令行/Web 共用）
├── main.py                  # 命令行入口（matplotlib 双子图可视化）
├── app.py                   # Flask Web 应用入口（提供 REST API）
├── templates/
│   └── index.html           # Web 前端单页面（参数面板 + ECharts 图表 + 信号表）
├── k-bar-1d/                # 日K线 CSV 数据目录
│   ├── price_510050.csv     # 50ETF
│   ├── price_510300.csv     # 300ETF
│   ├── price_600519.csv     # 贵州茅台
│   ├── price_601318.csv     # 中国平安
│   ├── price_601398.csv     # 工商银行
│   ├── price_000776.csv     # 广发证券
│   └── price_002594.csv     # 比亚迪
├── spec.md                  # 策略量化逻辑规格说明
└── README.md                # 本文件
~~~

### 模块职责

~~~mermaid
graph LR
    A["analysis.py 核心分析"] --> B["main.py 命令行入口"]
    A --> C["app.py Web 后端"]
    C --> D["templates/index.html 前端 UI"]
    E["k-bar-1d/*.csv 原始数据"] --> A
~~~

---

## 核心算法思路

### 概念说明

**惯性突破（标准图）** 是一种基于「假跌破后快速反转」的趋势交易形态：
价格因恐慌情绪短暂跌破关键支撑位，但杀跌动能迅速衰竭，主力资金借机吸筹推动价格快速站回支撑位上方，形成"诱空"陷阱。

### 五步量化逻辑

~~~mermaid
flowchart TD
    Start([遍历每根K线 t]) --> Step1["Step 1 计算支撑边界"]
    Step1 --> Step2{"Step 2 窗口内是否发生跌破"}
    Step2 -- 否 --> Skip([跳过])
    Step2 -- 是 --> Step3{"Step 3 是否出现停顿迹象 小实体或长下影线"}
    Step3 -- 否 --> Skip
    Step3 -- 是 --> Step4{"Step 4a 当日收盘 站回 支撑位"}
    Step4 -- 否 --> Skip
    Step4 -- 是 --> Step5{"Step 4b 成交量大于均量倍数"}
    Step5 -- 否 --> Skip
    Step5 -- 是 --> Signal["Step 5 触发信号 记录 进场价 支撑位 止损价"]
    Signal --> Next([下一根K线])
    Skip --> Next
~~~

### 关键判定条件

| 步骤 | 判定逻辑 | 对应 CONFIG 参数 |
|---|---|---|
| 1. 支撑边界 | Support = MIN(low[t-Lookback : t-Window]) | `lookback_period` |
| 2. 跌破识别 | close[t-i] < Support（i ∈ [1, Window]） | `breakout_window` |
| 3. 停顿减速 | 实体比例 < 阈值 或 下影线占比 > 阈值 | `small_body_ratio` / `lower_shadow_ratio` |
| 4. 站回确认 | close[t] > Support 且 (open[t] < Support 或 close[t-1] < Support) | — |
| 4. 量能验证 | volume[t] > MA(volume) × 倍数 | `volume_ma_period` / `vol_surge_ratio` |
| 5. 风险设置 | Stop_Loss = Lowest_Since_Break × 缓冲系数 | `stop_loss_buffer` |

### Web 应用数据流

~~~mermaid
sequenceDiagram
    participant U as 用户浏览器
    participant F as Flask app.py
    participant A as analysis.py
    participant D as CSV 数据
    U->>F: GET / 加载页面
    F-->>U: 渲染 index.html
    U->>U: 调整参数 / 选择文件
    U->>F: POST /api/analyze
    F->>A: load_data + detect_break_flip
    A->>D: 读取 CSV
    D-->>A: DataFrame
    A-->>F: 带信号的 DataFrame
    F-->>U: JSON 价格序列 + 信号列表
    U->>U: ECharts 渲染图表 + 表格
    U->>F: POST /api/export
    F-->>U: 下载 CSV
~~~

---

## 安装与启动

### 环境要求

- Python ≥ 3.9
- Windows / macOS / Linux

### 安装依赖

~~~bash
pip install flask pandas numpy matplotlib
~~~

### 方式一：Web 应用（推荐）

~~~bash
cd break_flip
python app.py
~~~

启动后浏览器访问：`http://127.0.0.1:18050`

### 方式二：命令行（matplotlib 弹窗）

~~~bash
cd break_flip
python main.py
~~~

如需更换标的或调参，编辑 `main.py` 中的 `CONFIG` 字典。

---

## 使用指引

### Web 应用界面布局

~~~mermaid
graph TB
    subgraph 左侧["左侧参数面板"]
        L1[数据来源 选择/上传]
        L2[起始日期]
        L3[支撑位参数]
        L4[跌破参数]
        L5[停顿减速参数]
        L6[成交量参数]
        L7[止损参数]
        L8[开始分析按钮]
    end
    subgraph 右侧["右侧主区域"]
        R1[结果信息条]
        R2[ECharts 图表区]
        R3[信号表格]
        R4[导出CSV按钮]
    end
~~~

### 操作流程

1. **选择数据源**
   - 「选择已有文件」：从 `k-bar-1d/` 目录下拉选择
   - 「上传 CSV」：本地选择任意符合格式的 CSV
2. **调整参数**：根据标的特性微调（建议先用默认值）
3. **点击「开始分析」**：等待几秒，图表会显示K线、信号点（红▲）、支撑位（绿▬）
4. **查看信号**：下方表格列出所有检测到的信号详情
5. **导出结果**：点击「导出 CSV」下载 `<标的代码>_signals.csv`

### 命令行使用示例

修改 `main.py`：

~~~python
CONFIG = {
    "data_file": r"./k-bar-1d/price_510300.csv",
    "start_date": "2010-01-01",
    "lookback_period": 20,
    "breakout_window": 5,
    "vol_surge_ratio": 1.2,
}
~~~

运行后将弹出 matplotlib 双子图（价格+信号 / 成交量+均量），并在控制台打印每一个信号的详细日志：

~~~
[INFO] 信号 #1 | 日期: 2014-05-12 | 进场价: 1.2250 | 支撑位: 1.2040 | 止损价: 1.1860
~~~

---

## 策略参数说明

| 参数 | 类型 | 默认值 | 说明 | 调参建议 |
|---|---|---|---|---|
| `start_date` | str | `2010-01-01` | 数据过滤起始日期 | 根据回测时间窗口调整 |
| `lookback_period` | int | 20 | 寻找支撑边界的回溯天数 | 20-60 |
| `breakout_window` | int | 5 | 假跌破在外停留的最大天数 | 严格限制为 3-5 |
| `small_body_ratio` | float | 0.01 | 停顿K线实体比例阈值 | 越小越严格 |
| `lower_shadow_ratio` | float | 0.4 | 下影线占总振幅的比例阈值 | 0.4-0.6 |
| `volume_ma_period` | int | 20 | 成交量均线周期 | 与 lookback 同量级 |
| `vol_surge_ratio` | float | 1.2 | 站回当日的放量倍数 | 1.2-2.0 |
| `stop_loss_buffer` | float | 0.99 | 止损系数 | 0.97-0.99 |

---

## 数据格式

CSV 文件需包含以下列（顺序无关）：

| 列名 | 类型 | 说明 |
|---|---|---|
| `timetag` | int | 日期，格式 YYYYMMDD（如 20240115） |
| `open` | float | 开盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `close` | float | 收盘价 |
| `volumn` 或 `volume` | float | 成交量（兼容拼写） |
| `amount` | float | 成交额（可选） |

**示例**（`price_510050.csv` 节选）：

~~~
timetag,open,high,low,close,volumn,amount
20050223,0.607,0.608,0.597,0.604,12697425.0,1111793167.00
20050224,0.604,0.604,0.598,0.604,4516142.0,394141216.00
~~~

---

## 常见问题

### Q1：Web 应用启动后访问 405 / 端口冲突

A：确认端口 18050 未被占用。如冲突，修改 `app.py` 末尾 `port=18050` 为其他端口。

### Q2：检测不到任何信号？

A：参数过严，按以下顺序放宽：

1. `vol_surge_ratio`: 1.5 → 1.2 → 1.0
2. `small_body_ratio`: 0.005 → 0.01 → 0.02
3. `lower_shadow_ratio`: 0.5 → 0.4 → 0.3

### Q3：matplotlib 中文显示为方框？

A：`main.py` 已配置 Microsoft YaHei 字体，若仍异常，安装中文字体或修改 `matplotlib.rcParams["font.sans-serif"]`。

### Q4：上传的 CSV 报错？

A：检查列名是否包含 `timetag, open, high, low, close, volumn`（注意 volumn 是数据原始拼写，已自动兼容 volume）。

---

## 策略风险声明

⚠️ 本项目仅作为技术学习与策略研究工具，**不构成任何投资建议**。  
量化信号回测结果不代表未来收益，实盘交易请独立判断并自负盈亏。

---

## License

MIT