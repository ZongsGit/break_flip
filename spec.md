
### 技术栈要求
全程采用python及其扩展库，保证扩展性
关键结果需要打印log
各个处理步骤需要清晰划分，核心逻辑需要采用config配置参数，便于调试对比

### 需求目标
将「惯性突破」（标准图）从视觉上的主观形态转化为可量化执行的趋势交易信号，核心在于将“寻找边界”、“假跌破”、“停顿减速”与“带量站回”这四个动作转化为数学与逻辑条件。

以下是基于日K线数据 `(timetag, open, high, low, close, volume, amount)` 提取惯性突破「标准图」交易信号的伪代码流程及逻辑解析：

### 1. 惯性突破信号的量化逻辑定义
*   **寻找关键边界（支撑位）：** 过去一段时间内（如20-60个交易日）市场多次测试但未跌破的最低点区域。
*   **假跌破（破底）：** 价格以实质性阴线跌破该支撑边界，创出新低。
*   **停顿与减速（测底）：** 跌破后并未引发持续性的瀑布式下跌，而是出现实体极小的K线（如十字星）或带有长下影线的K线，表明杀跌动能衰竭。
*   **确认站回（翻）：** 在跌破后的短时间内（如3-5天内），收盘价迅速由下而上重新站回原支撑边界之上，且通常伴随成交量（Volume）或成交额（Amount）的放大。

### 2. 伪代码流程 (Pseudo-code)

```python
// 定义输入数据结构为日K线序列
// K线数据包含: timetag, open, high, low, close, volume, amount

// 策略参数初始化
Lookback_Period = 20      // 寻找关键支撑边界的回溯期
Breakout_Window = 5       // 允许假跌破在外停留的最大天数（迅速站回的时间窗口）
Volume_MA_Period = 20     // 成交量均线周期
Vol_Surge_Ratio = 1.5     // 确认站回时的放量倍数阈值
Small_Body_Ratio = 0.005  // 定义“停顿”K线的实体最大比例阈值

// 遍历每一天的日K数据
FOR t FROM Lookback_Period TO Current_Day:
    
    // 1. 定义前期关键支撑边界 (Support_Level)
    // 取前一时期内的最低收盘价或最低价作为关键边界
    Support_Level = MIN(low[t - Lookback_Period : t - Breakout_Window])
    
    // 2. 识别“跌破”动作
    // 在过去Breakout_Window天内，是否发生过收盘价跌破支撑边界
    Is_Broken = FALSE
    Lowest_Price_Since_Break = 999999
    Days_Since_Break = 0
    
    FOR i FROM 1 TO Breakout_Window:
        IF close[t - i] < Support_Level:
            Is_Broken = TRUE
            Lowest_Price_Since_Break = MIN(Lowest_Price_Since_Break, low[t - i])
            Days_Since_Break = i
            BREAK // 记录最近一次跌破
            
    // 3. 识别“停顿与减速” (K线实体缩窄或留有长下影线)
    // 检查跌破期间的K线是否出现停顿迹象
    Is_Decelerated = FALSE
    IF Is_Broken:
        // 计算跌破当日或其后一日的K线实体大小
        K_Body_Size = ABS(close[t-1] - open[t-1]) / close[t-1]
        // 或者是长下影线 (收盘价远高于最低价)
        Lower_Shadow = min(open[t-1], close[t-1]) - low[t-1]
        Total_Range = high[t-1] - low[t-1]
        
        IF (K_Body_Size < Small_Body_Ratio) OR (Lower_Shadow > 0.5 * Total_Range):
            Is_Decelerated = TRUE

    // 4. 识别“站回”与“成交量验证”动作 (惯性突破确认)
    // 当日收盘价重新由下往上站回支撑边界
    Is_Reclaimed = (close[t] > Support_Level) AND (open[t] < Support_Level OR close[t-1] < Support_Level)
    
    // 成交量验证：真实的突破/反转必须伴随成交量爆发（如大于20日均量的1.5倍）
    Avg_Volume = AVERAGE(volume[t-Volume_MA_Period : t-1])
    Is_Vol_Confirmed = volume[t] > (Avg_Volume * Vol_Surge_Ratio)
    
    // 5. 触发交易信号
    IF Is_Broken AND Is_Decelerated AND Is_Reclaimed AND Is_Vol_Confirmed:
        
        // 记录进场与止损信息
        Signal_Time = timetag[t]
        Entry_Price = close[t]
        // 止损点设在假跌破创出的绝对新低下方
        Stop_Loss = Lowest_Price_Since_Break * 0.99  
        
        PRINT "在时间", Signal_Time, "检测到标准图(惯性突破)信号!"
        PRINT "进场价:", Entry_Price, "| 止损价:", Stop_Loss
        
        EXECUTE_BUY_ORDER(amount = Calculate_Position_Size(Stop_Loss))
```

### 3. 伪代码参数与逻辑解析

1. **边界过滤（Support_Level）：** 代码中选取了回溯期内的最低点作为“关键边界”。在实盘中，可以使用更复杂的聚类算法（如价格密集区识别）来替代简单的 `MIN()`，以确保这个边界是“多空激烈争夺过的天花板或地板”。
2. **时间窗口（Breakout_Window）：** 标准图的核心是“跌破后迅速站回”。如果跌破后在下方盘整了20天还没站回，这就不叫假跌破，而是趋势向下延续。因此严格限制 `Breakout_Window = 5`，强迫系统只抓取诱空型的快速反转。
3. **减速验证（Is_Decelerated）：** 市场跌破边界时，如果像全速冲刺的火车一样（大实体阴线）直接贯穿，绝不能立刻做多。伪代码通过 `K_Body_Size < 0.005`（极小实体十字星）或下影线占据整根K线一半以上（强劲买盘托底）来量化“停顿”的动作。
4. **量能确认（Volume & Amount）：** 假突破往往是在低成交量下发生的，而真实的“站回”必须带有机构参与的痕迹。通过 `volume[t] > (Avg_Volume * 1.5)` 过滤掉无量的假反弹，确保站回的有效性。
5. **风险管理（Stop_Loss）：** 信号一旦成立，止损位（Stop Loss）必须设置在惯性突破创下的“假跌破最低点”下方（`Lowest_Price_Since_Break`）。如果后续价格再次跌破该低点，说明“惯性突破”失败，趋势继续向下，必须严格切断亏损。