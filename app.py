"""
惯性突破（标准图）量化信号检测 —— Flask Web 应用
"""

import os
import io
import glob
import logging
import tempfile

import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file

from analysis import DEFAULT_CONFIG, load_data, detect_break_flip, get_stock_code

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "k-bar-1d")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB


def _list_available_files():
    """列出 k-bar-1d 目录下所有 CSV 文件"""
    pattern = os.path.join(DATA_DIR, "*.csv")
    files = sorted(glob.glob(pattern))
    return [os.path.basename(f) for f in files]


def _parse_config(form_data):
    """从请求表单中解析策略参数，缺失则用默认值"""
    cfg = dict(DEFAULT_CONFIG)
    int_keys = ["lookback_period", "breakout_window", "volume_ma_period"]
    float_keys = ["small_body_ratio", "lower_shadow_ratio", "vol_surge_ratio", "stop_loss_buffer"]

    for k in int_keys:
        if k in form_data and form_data[k]:
            cfg[k] = int(form_data[k])
    for k in float_keys:
        if k in form_data and form_data[k]:
            cfg[k] = float(form_data[k])
    if "start_date" in form_data and form_data["start_date"]:
        cfg["start_date"] = form_data["start_date"]
    return cfg


def _resolve_data_file(req):
    """
    根据请求决定数据文件路径：
      - 如果上传了文件，保存到临时目录并返回路径
      - 否则使用选择的已有文件
    返回 (file_path, stock_code, temp_path_or_None)
    """
    temp_path = None

    if "csv_file" in req.files and req.files["csv_file"].filename:
        uploaded = req.files["csv_file"]
        temp_path = os.path.join(tempfile.gettempdir(), uploaded.filename)
        uploaded.save(temp_path)
        file_path = temp_path
        stock_code = get_stock_code(uploaded.filename)
        logger.info("使用上传文件: %s", uploaded.filename)
    else:
        selected = req.form.get("selected_file", "")
        if not selected:
            selected = _list_available_files()[0] if _list_available_files() else ""
        file_path = os.path.join(DATA_DIR, selected)
        stock_code = get_stock_code(selected)
        logger.info("使用已有文件: %s", selected)

    return file_path, stock_code, temp_path


def _run_analysis(req):
    """执行分析流程，返回 (df, cfg, stock_code, temp_path)"""
    cfg = _parse_config(req.form)
    file_path, stock_code, temp_path = _resolve_data_file(req)

    df = load_data(file_path, cfg["start_date"])
    df = detect_break_flip(df, cfg)

    return df, cfg, stock_code, temp_path


# ============================================================
# 路由
# ============================================================
@app.route("/", methods=["GET"])
def index():
    files = _list_available_files()
    logger.info("GET / -> files=%s", files)
    return render_template("index.html", files=files, config=DEFAULT_CONFIG)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """执行分析，返回 JSON 结果（价格序列 + 信号列表）"""
    try:
        df, cfg, stock_code, temp_path = _run_analysis(request)

        # 价格数据（降采样：如数据量大只发送关键列）
        price_data = {
            "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
            "open": df["open"].round(4).tolist(),
            "high": df["high"].round(4).tolist(),
            "low": df["low"].round(4).tolist(),
            "close": df["close"].round(4).tolist(),
            "volume": df["volume"].tolist(),
            "vol_ma": df["vol_ma"].round(0).fillna(0).tolist(),
        }

        # 信号数据
        signals_df = df[df["signal"]].copy()
        signals = []
        for _, row in signals_df.iterrows():
            signals.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "entry_price": round(row["entry_price"], 4),
                "support_level": round(row["support_level"], 4),
                "stop_loss": round(row["stop_loss"], 4),
            })

        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({
            "success": True,
            "stock_code": stock_code,
            "config": cfg,
            "total_bars": len(df),
            "signal_count": len(signals),
            "price_data": price_data,
            "signals": signals,
        })

    except Exception as e:
        logger.exception("分析出错")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/export", methods=["POST"])
def api_export():
    """执行分析，返回信号表 CSV 文件下载"""
    try:
        df, cfg, stock_code, temp_path = _run_analysis(request)

        signals_df = df[df["signal"]][["date", "entry_price", "support_level", "stop_loss"]].copy()
        signals_df["date"] = signals_df["date"].dt.strftime("%Y-%m-%d")
        signals_df.columns = ["日期", "进场价", "支撑位", "止损价"]

        buf = io.BytesIO()
        signals_df.to_csv(buf, index=False, encoding="utf-8-sig")
        buf.seek(0)

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        return send_file(
            buf,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{stock_code}_signals.csv",
        )

    except Exception as e:
        logger.exception("导出出错")
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    logger.info("启动 Web 应用: http://127.0.0.1:18050")
    app.run(debug=False, host="127.0.0.1", port=18050)
