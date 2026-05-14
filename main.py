"""
惯性突破（标准图）量化信号检测与可视化工具 —— 命令行入口
"""

import os
import logging
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from analysis import DEFAULT_CONFIG, load_data, detect_break_flip, get_stock_code

# Windows 中文字体支持
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 命令行使用的参数（可在此覆盖默认值）
CONFIG = dict(DEFAULT_CONFIG)


# ============================================================
# 可视化输出
# ============================================================
def plot_signals(df, cfg, data_file):
    """
    双子图可视化：
      上图 —— 收盘价走势 + 信号标注（进场/止损）
      下图 —— 成交量柱状图 + 均量线
    """
    signals = df[df["signal"]].copy()

    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1, figsize=(18, 10),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )

    # 上图: 价格与信号
    ax_price.plot(df["date"], df["close"], color="#34495e", linewidth=0.8, alpha=0.7, label="Close Price")

    if not signals.empty:
        ax_price.scatter(
            signals["date"], signals["entry_price"],
            color="#e74c3c", marker="^", s=100, zorder=5,
            label=f"惯性突破信号 ({len(signals)}个)",
        )
        for _, row in signals.iterrows():
            ax_price.plot(
                [row["date"], row["date"]],
                [row["stop_loss"], row["entry_price"]],
                color="#e67e22", linewidth=1.2, alpha=0.6,
            )
        ax_price.scatter(
            signals["date"], signals["support_level"],
            color="#2ecc71", marker="_", s=120, linewidths=2, zorder=4,
            label="Support Level",
        )

    stock_code = get_stock_code(data_file)
    ax_price.set_title(
        f"{stock_code} 惯性突破（标准图）信号检测  |  "
        f"回溯={cfg['lookback_period']}  窗口={cfg['breakout_window']}  "
        f"放量倍数={cfg['vol_surge_ratio']}",
        fontsize=14,
    )
    ax_price.set_ylabel("Price")
    ax_price.legend(loc="upper left", fontsize=9)
    ax_price.grid(True, linestyle="--", alpha=0.3)

    # 下图: 成交量
    colors = ["#e74c3c" if c < o else "#2ecc71" for c, o in zip(df["close"], df["open"])]
    ax_vol.bar(df["date"], df["volume"], color=colors, alpha=0.5, width=2)
    ax_vol.plot(df["date"], df["vol_ma"], color="#e67e22", linewidth=1, label=f"Vol MA({cfg['volume_ma_period']})")
    ax_vol.set_ylabel("Volume")
    ax_vol.legend(loc="upper left", fontsize=9)
    ax_vol.grid(True, linestyle="--", alpha=0.3)

    ax_vol.xaxis.set_major_locator(mdates.YearLocator())
    ax_vol.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# ============================================================
# 主流程
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("惯性突破（标准图）量化信号检测工具启动")
    logger.info("=" * 60)

    logger.info("当前策略参数:")
    for k, v in CONFIG.items():
        logger.info("  %-25s = %s", k, v)

    data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG["data_file"])
    df = load_data(data_file, CONFIG["start_date"])
    df = detect_break_flip(df, CONFIG)

    signals = df[df["signal"]]
    if signals.empty:
        logger.info("未检测到任何惯性突破信号，可尝试调整 CONFIG 参数。")
    else:
        logger.info("=" * 60)
        logger.info("信号汇总（共 %d 个）:", len(signals))
        logger.info("-" * 60)
        for _, row in signals.iterrows():
            logger.info(
                "  %s  进场: %.4f  支撑: %.4f  止损: %.4f",
                row["date"].strftime("%Y-%m-%d"),
                row["entry_price"],
                row["support_level"],
                row["stop_loss"],
            )
        logger.info("=" * 60)

    plot_signals(df, CONFIG, data_file)


if __name__ == "__main__":
    main()
