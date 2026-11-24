import numpy as np
import pandas as pd


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]

    # RSI (14) - làm mượt kiểu Wilder
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["rsi14"] = 100 - 100 / (1 + rs)

    # SMA
    for n in (20, 50, 200):
        out[f"sma{n}"] = close.rolling(n).mean()

    # EMA
    for n in (12, 26):
        out[f"ema{n}"] = close.ewm(span=n, adjust=False).mean()

    # MACD (12, 26, 9)
    out["macd"] = out["ema12"] - out["ema26"]
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    # Bollinger Bands (20, 2)
    std20 = close.rolling(20).std(ddof=0)
    out["bb_mid"] = out["sma20"]
    out["bb_upper"] = out["bb_mid"] + 2 * std20
    out["bb_lower"] = out["bb_mid"] - 2 * std20

    # Volume trung bình 20 phiên
    out["vol_avg20"] = out["volume"].rolling(20).mean()

    return out


def explain_latest(df: pd.DataFrame) -> dict:
    """Giải thích tín hiệu hiện tại của từng chỉ báo (phiên cuối cùng)."""
    last, prev = df.iloc[-1], df.iloc[-2]
    r = {}

    # RSI
    rsi = last["rsi14"]
    if pd.isna(rsi):
        r["rsi"] = {"value": None, "signal": "N/A", "text": "Chưa đủ dữ liệu để tính RSI."}
    elif rsi >= 70:
        r["rsi"] = {"value": round(rsi, 2), "signal": "Bán", "text": f"RSI = {rsi:.1f} (≥70): vùng quá mua, giá có thể điều chỉnh."}
    elif rsi <= 30:
        r["rsi"] = {"value": round(rsi, 2), "signal": "Mua", "text": f"RSI = {rsi:.1f} (≤30): vùng quá bán, có thể xuất hiện nhịp hồi."}
    else:
        r["rsi"] = {"value": round(rsi, 2), "signal": "Chờ", "text": f"RSI = {rsi:.1f}: vùng trung tính (30–70), chưa có tín hiệu rõ."}

    # SMA
    sma_items = []
    for n in (20, 50, 200):
        v = last[f"sma{n}"]
        if pd.isna(v):
            sma_items.append({"period": n, "value": None, "text": f"Chưa đủ dữ liệu cho SMA{n}."})
        else:
            pos = "trên" if last["close"] > v else "dưới"
            sma_items.append({"period": n, "value": round(v, 2),
                              "text": f"Giá đang {pos} SMA{n} ({v:.2f}) → xu hướng {'tăng' if pos == 'trên' else 'giảm'} ở khung {n} phiên."})
    r["sma"] = sma_items

    # EMA
    ema12, ema26 = last["ema12"], last["ema26"]
    r["ema"] = {
        "ema12": round(ema12, 2), "ema26": round(ema26, 2),
        "signal": "Mua" if ema12 > ema26 else "Bán",
        "text": f"EMA12 {'trên' if ema12 > ema26 else 'dưới'} EMA26 → động lượng ngắn hạn {'tăng' if ema12 > ema26 else 'giảm'}.",
    }

    # MACD
    if pd.isna(last["macd_signal"]):
        r["macd"] = {"signal": "N/A", "text": "Chưa đủ dữ liệu để tính MACD."}
    else:
        cross_up = prev["macd"] <= prev["macd_signal"] and last["macd"] > last["macd_signal"]
        cross_dn = prev["macd"] >= prev["macd_signal"] and last["macd"] < last["macd_signal"]
        if cross_up:
            sig, txt = "Mua", "MACD vừa cắt LÊN đường tín hiệu: tín hiệu mua."
        elif cross_dn:
            sig, txt = "Bán", "MACD vừa cắt XUỐNG đường tín hiệu: tín hiệu bán."
        elif last["macd"] > last["macd_signal"]:
            sig, txt = "Mua", "MACD đang nằm trên đường tín hiệu: động lượng tăng."
        else:
            sig, txt = "Bán", "MACD đang nằm dưới đường tín hiệu: động lượng giảm."
        r["macd"] = {"macd": round(last["macd"], 3), "signal_line": round(last["macd_signal"], 3),
                     "histogram": round(last["macd_hist"], 3), "signal": sig, "text": txt}

    # Bollinger
    if pd.isna(last["bb_upper"]):
        r["bollinger"] = {"signal": "N/A", "text": "Chưa đủ dữ liệu để tính Bollinger Bands."}
    else:
        c = last["close"]
        if c >= last["bb_upper"]:
            sig, txt = "Bán", "Giá chạm/vượt dải trên: có thể quá mua ngắn hạn."
        elif c <= last["bb_lower"]:
            sig, txt = "Mua", "Giá chạm/thủng dải dưới: có thể quá bán ngắn hạn."
        else:
            sig, txt = "Chờ", "Giá nằm trong hai dải Bollinger: biến động bình thường."
        r["bollinger"] = {"upper": round(last["bb_upper"], 2), "middle": round(last["bb_mid"], 2),
                          "lower": round(last["bb_lower"], 2), "signal": sig, "text": txt}

    # Volume
    va = last["vol_avg20"]
    if pd.isna(va):
        r["volume"] = {"signal": "N/A", "text": "Chưa đủ dữ liệu volume trung bình."}
    else:
        ratio = last["volume"] / va
        if ratio >= 1.5:
            txt = f"Volume gấp {ratio:.1f} lần trung bình 20 phiên: dòng tiền mạnh, tín hiệu giá đáng tin hơn."
        elif ratio <= 0.6:
            txt = f"Volume chỉ bằng {ratio:.1f} lần trung bình: thanh khoản yếu, tín hiệu kém tin cậy."
        else:
            txt = f"Volume ≈ {ratio:.1f} lần trung bình 20 phiên: thanh khoản bình thường."
        r["volume"] = {"value": int(last["volume"]), "avg20": int(va), "ratio": round(ratio, 2), "text": txt}

    return r