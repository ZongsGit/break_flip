"""
惯性突破（标准图）核心分析模块
提供数据加载与信号检测功能，供命令行和 Web 应用共用。
"""

import os
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================
# 默认策略参数 CONFIG
# ============================================================
DEFAULT_CONFIG = {
    "data_file": r"./k-bar-1d/price_510050.csv",
    "start_date": "2005-01-01",
    "lookback_period": 20,
    "breakout_window": 5,
    "small_body_ratio": 0.01,
    "lower_shadow_ratio": 0.4,
    "volume_ma_period": 20,
    "vol_surge_ratio": 1.2,
    "stop_loss_buffer": 0.99,
}


# ============================================================
# 数据加载与预处理
# ============================================================
def load_data(file_path: str, start_date: str) -> pd.DataFrame:
    """加载 CSV 日K数据并做基础预处理"""
    logger.info("加载数据文件: %s", file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"数据文件不存在: {file_path}")

    df = pd.read_csv(file_path)
    df["date"] = pd.to_datetime(df["timetag"], format="%Y%m%d")
    df = df.sort_values("date").reset_index(drop=True)

    # CSV 中列名为 volumn（原始数据拼写），统一映射为 volume
    if "volumn" in df.columns and "volume" not in df.columns:
        df.rename(columns={"volumn": "volume"}, inplace=True)

    total_rows = len(df)
    df = df[df["date"] >= start_date].copy().reset_index(drop=True)
    logger.info("数据总行数: %d，过滤后保留: %d（起始日期 >= %s）", total_rows, len(df), start_date)
    return df


# ============================================================
# 惯性突破信号检测（核心逻辑）
# ============================================================
def detect_break_flip(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    逐行扫描日K数据，按五步逻辑检测惯性突破信号。
    返回包含信号标记列的 DataFrame。
    """
    lookback = cfg["lookback_period"]
    bw = cfg["breakout_window"]
    small_body = cfg["small_body_ratio"]
    shadow_ratio = cfg["lower_shadow_ratio"]
    vol_ma_period = cfg["volume_ma_period"]
    vol_surge = cfg["vol_surge_ratio"]
    sl_buffer = cfg["stop_loss_buffer"]

    n = len(df)
    df["vol_ma"] = df["volume"].rolling(window=vol_ma_period, min_periods=vol_ma_period).mean()

    df["signal"] = False
    df["support_level"] = np.nan
    df["entry_price"] = np.nan
    df["stop_loss"] = np.nan

    signal_count = 0
    min_start = lookback + bw

    logger.info("开始扫描惯性突破信号（lookback=%d, breakout_window=%d）...", lookback, bw)

    for t in range(min_start, n):
        # Step 1: 计算支撑边界
        support_start = t - lookback
        support_end = t - bw
        if support_end <= support_start:
            continue
        support_level = df["low"].iloc[support_start:support_end].min()

        # Step 2: 在 breakout_window 内寻找跌破
        is_broken = False
        lowest_since_break = np.inf
        break_days = []
        for i in range(1, bw + 1):
            idx = t - i
            if idx < 0:
                break
            if df["close"].iloc[idx] < support_level:
                is_broken = True
                lowest_since_break = min(lowest_since_break, df["low"].iloc[idx])
                break_days.append(idx)

        if not is_broken:
            continue

        # Step 3: 停顿与减速验证
        is_decelerated = False
        check_range = range(max(break_days[-1], t - bw), t)
        for chk in check_range:
            c_close = df["close"].iloc[chk]
            c_open = df["open"].iloc[chk]
            c_low = df["low"].iloc[chk]
            c_high = df["high"].iloc[chk]

            k_body_size = abs(c_close - c_open) / c_close if c_close != 0 else 0
            total_range = c_high - c_low
            lower_shadow = min(c_open, c_close) - c_low

            if k_body_size < small_body:
                is_decelerated = True
                break
            if total_range > 0 and (lower_shadow > shadow_ratio * total_range):
                is_decelerated = True
                break

        if not is_decelerated:
            continue

        # Step 4: 确认站回 + 成交量验证
        close_t = df["close"].iloc[t]
        open_t = df["open"].iloc[t]
        close_prev_t = df["close"].iloc[t - 1]

        is_reclaimed = (close_t > support_level) and (open_t < support_level or close_prev_t < support_level)

        avg_vol = df["vol_ma"].iloc[t]
        is_vol_confirmed = False
        if pd.notna(avg_vol) and avg_vol > 0:
            is_vol_confirmed = df["volume"].iloc[t] > (avg_vol * vol_surge)

        if not (is_reclaimed and is_vol_confirmed):
            continue

        # Step 5: 触发信号
        signal_time = df["date"].iloc[t]
        entry_price = close_t
        stop_loss = lowest_since_break * sl_buffer

        df.at[t, "signal"] = True
        df.at[t, "support_level"] = support_level
        df.at[t, "entry_price"] = entry_price
        df.at[t, "stop_loss"] = stop_loss
        signal_count += 1

        logger.info(
            "信号 #%d | 日期: %s | 进场价: %.4f | 支撑位: %.4f | 止损价: %.4f",
            signal_count,
            signal_time.strftime("%Y-%m-%d"),
            entry_price,
            support_level,
            stop_loss,
        )

    logger.info("扫描完毕，共检测到 %d 个惯性突破信号。", signal_count)
    return df


def get_stock_code(file_path: str) -> str:
    """从文件路径中提取标的代码"""
    return os.path.splitext(os.path.basename(file_path))[0].replace("price_", "")
