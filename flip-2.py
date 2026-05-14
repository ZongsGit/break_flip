
"""
维度对应参数调优逻辑性价比过滤value_ratio_threshold0.95 意味着只做“越来越便宜”的反转，过滤横盘。
反转力度recovery_threshold设为 0.01 可以过滤掉那些收盘价仅勉强站回支撑线的弱势反弹。
趋势宽容度ema_window增大至 60 可以更长时间地留在趋势中，但会牺牲卖点的灵敏度。
止损安全性sl_buffer信号日低点下方的空间，防止被市场噪点（Noise）随机扫损。
"""

c
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

def analyze_break_low_flip_pro(file_path, params):
    """
    破低翻增强型策略回测与可视化函数
    """
    # --- 1. 数据加载与指标计算 ---
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['timetag'], format='%Y%m%d')
    df = df.sort_values('date').set_index('date')
    df = df[df.index >= params['start_date']]
    
    # 基础支撑位与趋势线
    df['support'] = df['low'].shift(1).rolling(window=params['window']).min()
    df['vol_ma'] = df['volumn'].rolling(window=10).mean()
    df['ema_exit'] = df['close'].ewm(span=params['ema_window'], adjust=False).mean()
    
    # --- 2. 状态机回测 ---
    df['position'] = 0
    df['entry_signal'] = False
    df['exit_signal'] = False
    
    in_position = False
    stop_loss_price = 0.0
    history_prices = deque(maxlen=params['prev_signal_count'])
    
    for i in range(len(df)):
        curr_idx = df.index[i]
        row = df.iloc[i]
        
        if not in_position:
            # A. 基础形态判断
            base_trigger = (row['low'] < row['support']) and \
                           (row['close'] > row['support'] * (1 + params['recovery_threshold'])) and \
                           (row['volumn'] > row['vol_ma'] * params['vol_multiplier'])
            
            # B. 递归价格过滤 (Price Filter)
            price_filter = True
            if base_trigger and len(history_prices) == params['prev_signal_count']:
                avg_prev = sum(history_prices) / len(history_prices)
                # 判定公式: Current Price < Average(Prev N) * Ratio
                if row['close'] >= avg_prev * params['value_ratio_threshold']:
                    price_filter = False
            
            if base_trigger and price_filter:
                in_position = True
                stop_loss_price = row['low'] * (1 - params['sl_buffer'])
                df.at[curr_idx, 'entry_signal'] = True
                df.at[curr_idx, 'position'] = 1
                history_prices.append(row['close'])
        else:
            # C. 离场判定 (止损线 或 EMA死叉)
            if (row['low'] < stop_loss_price) or (row['close'] < row['ema_exit']):
                in_position = False
                df.at[curr_idx, 'exit_signal'] = True
                df.at[curr_idx, 'position'] = 0
            else:
                df.at[curr_idx, 'position'] = 1

    # --- 3. 可视化看板 ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # 主图: 价格与信号
    ax1.plot(df.index, df['close'], label='Close Price', color='#2c3e50', alpha=0.4, linewidth=1)
    ax1.plot(df.index, df['ema_exit'], label=f'EMA({params["ema_window"]})', color='#e67e22', linestyle='--', alpha=0.8)
    
    # 标注信号
    entries = df[df['entry_signal']]
    exits = df[df['exit_signal']]
    ax1.scatter(entries.index, entries['close'], color='#e74c3c', marker='^', s=120, label='ENTRY (Value Flip)', zorder=5)
    ax1.scatter(exits.index, exits['close'], color='#27ae60', marker='v', s=120, label='EXIT', zorder=5)
    
    ax1.set_title(f"A50 Pro Strategy: Break-Low-Flip (Price Filter: {params['value_ratio_threshold']})", fontsize=15)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.2)
    
    # 副图: 持仓状态
    ax2.fill_between(df.index, 0, df['position'], color='#3498db', alpha=0.3, label='Exposure')
    ax2.set_ylabel("Position State (0/1)")
    ax2.set_ylim(0, 1.1)
    ax2.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.show()
    
    return df

# --- 4. 运行实例 ---
my_params = {
    'start_date': '2013-01-01',
    'window': 20,                  # 支撑位窗口
    'recovery_threshold': 0.003,    # 翻转幅度
    'vol_multiplier': 1.1,         # 量能倍数
    'ema_window': 20,              # 离场趋势线
    'sl_buffer': 0.002,            # 止损缓冲
    'prev_signal_count': 1,        # 过滤参考信号数
    'value_ratio_threshold': 0.99  # 相对价格阈值
}

# 假设文件已在当前工作目录下，如果不在请提供完整路径
df_final = analyze_break_low_flip_pro('price_510050.csv', my_params)