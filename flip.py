import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetimec

# 1. 加载数据
file_path = 'price_510050.csv'
df = pd.read_csv(file_path)

# 2. 数据预处理
# 将 timetag 转换为日期格式，并按时间排序
df['date'] = pd.to_datetime(df['timetag'], format='%Y%m%d')
df = df.sort_values('date')

# 仅保留最近 10 年的数据 (从 2014 年左右开始)
df = df[df['date'] >= '2014-01-01'].copy()

# 3. 破低翻逻辑实现
def detect_break_low_flip(df, window=20):
    # 计算前 window 天的最低价（支撑位），不包含当前日
    df['prev_low'] = df['low'].shift(1).rolling(window=window).min()
    
    # 捕捉信号：
    # 条件A: 今日最低价跌破了过去N天的最低位 (破低)
    # 条件B: 今日收盘价重新站回过去N天的最低位之上 (翻)
    df['signal'] = (df['low'] < df['prev_low']) & (df['close'] > df['prev_low'])
    return df

df = detect_break_low_flip(df)

# 4. 可视化
plt.figure(figsize=(16, 8))
plt.plot(df['date'], df['close'], label='A50 Close Price', color='steelblue', alpha=0.6)

# 标注信号点
signals = df[df['signal'] == True]
plt.scatter(signals['date'], signals['low'], color='red', marker='^', label='Break Low & Flip Signal', s=80)

plt.title('A50 (510050) "Break Low and Flip" Strategy Detection (Last 10 Years)')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.4)
plt.show()

# 输出最近的 5 个信号日期
print("最近出现的破低翻机会：")
print(signals[['date', 'low', 'prev_low', 'close']].tail(5))