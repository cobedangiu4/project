"""Tổng hợp tín hiệu chỉ báo + mô hình nến thành kiến nghị Mua / Bán / Chờ."""
import pandas as pd

SIGNAL_W = {"Mua": 1.0, "Bán": -1.0, "Chờ": 0.0}
CONF_W = {"cao": 1.5, "trung bình": 1.0, "thấp": 0.5}
AGE_DECAY = [1.0, 0.7, 0.5]  # mô hình xuất hiện hôm nay / 1 phiên trước / 2 phiên trước


def recommend(df: pd.DataFrame, analysis: dict, patterns: list) -> dict:
    score = 0.0
    reasons = []

    for key, label in (("rsi", "RSI"), ("ema", "EMA 12/26"), ("macd", "MACD"), ("bollinger", "Bollinger")):
        item = analysis.get(key, {})
        w = SIGNAL_W.get(item.get("signal"), 0.0)
        if w:
            score += w
            reasons.append({"source": label, "effect": item["signal"], "text": item["text"]})

    last = df.iloc[-1]
    for n in (50, 200):
        v = last[f"sma{n}"]
        if pd.isna(v):
            continue
        above = bool(last["close"] > v)
        score += 0.5 if above else -0.5
        reasons.append({
            "source": f"SMA{n}", "effect": "Mua" if above else "Bán",
            "text": f"Giá đang {'trên' if above else 'dưới'} SMA{n} ({v:.2f}).",
        })

    n_rows = len(df)
    for p in patterns:
        age = n_rows - 1 - p["index"]
        if age > 2 or p["type"] == "neutral":
            continue
        w = CONF_W[p["confidence"]] * AGE_DECAY[age] * (1 if p["type"] == "bullish" else -1)
        score += w
        when = "hôm nay" if age == 0 else f"{age} phiên trước"
        reasons.append({
            "source": "Mô hình nến", "effect": "Mua" if w > 0 else "Bán",
            "text": f"{p['name_vi']} ({when}, độ tin cậy {p['confidence']}).",
        })

    action = "Mua" if score >= 2 else "Bán" if score <= -2 else "Chờ"
    mag = abs(score)
    strength = "Mạnh" if mag >= 3.5 else "Vừa" if mag >= 2 else "Yếu"

    summaries = {
        "Mua": "Đa số tín hiệu nghiêng về phía tăng giá.",
        "Bán": "Đa số tín hiệu nghiêng về phía giảm giá.",
        "Chờ": "Tín hiệu trái chiều hoặc chưa đủ rõ, nên quan sát thêm.",
    }
    return {
        "action": action,
        "score": round(score, 2),
        "strength": strength,
        "summary": summaries[action],
        "reasons": reasons,
        "disclaimer": "Kết quả do thuật toán đơn giản tạo ra từ dữ liệu quá khứ, "
                      "chỉ mang tính tham khảo, không phải lời khuyên đầu tư.",
    }