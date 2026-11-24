"""Nhận diện mô hình nến Nhật cơ bản trên dữ liệu nến ngày."""
import numpy as np
import pandas as pd

TREND_LOOKBACK = 5      # số phiên nhìn lại để xác định xu hướng trước mô hình
TREND_THRESHOLD = 0.03  # ±3% trong 5 phiên: coi là có xu hướng
STRONG_TREND = 0.06     # ±6%: xu hướng mạnh

META = {
    "doji": dict(vi="Doji", short="Doji", type="neutral", candles=1,
        text="Giá mở cửa và đóng cửa gần bằng nhau: phe mua và phe bán giằng co, thị trường do dự. "
             "Sau một xu hướng rõ, Doji báo hiệu xu hướng đó có thể yếu đi, nhưng cần nến sau xác nhận."),
    "hammer": dict(vi="Nến Búa (Hammer)", short="Búa", type="bullish", candles=1,
        text="Thân nhỏ nằm trên cùng, bóng dưới dài: giá bị đẩy xuống mạnh nhưng phe mua kéo lên lại. "
             "Xuất hiện sau nhịp giảm, đây là tín hiệu đảo chiều tăng tiềm năng."),
    "inverted_hammer": dict(vi="Búa ngược (Inverted Hammer)", short="Búa ngược", type="bullish", candles=1,
        text="Thân nhỏ nằm dưới, bóng trên dài: phe mua bắt đầu thử đẩy giá lên sau nhịp giảm. "
             "Tín hiệu đảo chiều tăng yếu hơn Búa, nên chờ nến tăng xác nhận ở phiên sau."),
    "shooting_star": dict(vi="Sao băng (Shooting Star)", short="Sao băng", type="bearish", candles=1,
        text="Thân nhỏ nằm dưới, bóng trên dài: giá bị đẩy lên cao rồi bị phe bán đè xuống. "
             "Xuất hiện sau nhịp tăng, đây là tín hiệu đảo chiều giảm tiềm năng."),
    "bullish_engulfing": dict(vi="Nhấn chìm tăng (Bullish Engulfing)", short="Nhấn chìm ↑", type="bullish", candles=2,
        text="Nến tăng có thân bao trùm hoàn toàn thân nến giảm trước đó: phe mua chiếm ưu thế rõ rệt sau nhịp giảm. "
             "Là tín hiệu đảo chiều tăng khá mạnh, đáng tin hơn khi volume lớn."),
    "bearish_engulfing": dict(vi="Nhấn chìm giảm (Bearish Engulfing)", short="Nhấn chìm ↓", type="bearish", candles=2,
        text="Nến giảm có thân bao trùm hoàn toàn thân nến tăng trước đó: phe bán chiếm ưu thế sau nhịp tăng. "
             "Là tín hiệu đảo chiều giảm khá mạnh, đáng tin hơn khi volume lớn."),
    "morning_star": dict(vi="Sao mai (Morning Star)", short="Sao mai", type="bullish", candles=3,
        text="Ba nến: nến giảm dài, nến thân nhỏ (do dự), rồi nến tăng đóng cửa sâu vào thân nến đầu. "
             "Đây là mô hình đảo chiều tăng đáng tin cậy sau nhịp giảm."),
    "evening_star": dict(vi="Sao hôm (Evening Star)", short="Sao hôm", type="bearish", candles=3,
        text="Ba nến: nến tăng dài, nến thân nhỏ (do dự), rồi nến giảm đóng cửa sâu vào thân nến đầu. "
             "Đây là mô hình đảo chiều giảm đáng tin cậy sau nhịp tăng."),
    "bullish_harami": dict(vi="Harami tăng (Bullish Harami)", short="Harami ↑", type="bullish", candles=2,
        text="Nến tăng nhỏ nằm gọn trong thân nến giảm dài trước đó: đà giảm chững lại. "
             "Tín hiệu đảo chiều tăng khá yếu, cần nến sau xác nhận."),
    "bearish_harami": dict(vi="Harami giảm (Bearish Harami)", short="Harami ↓", type="bearish", candles=2,
        text="Nến giảm nhỏ nằm gọn trong thân nến tăng dài trước đó: đà tăng chững lại. "
             "Tín hiệu đảo chiều giảm khá yếu, cần nến sau xác nhận."),
    "piercing_line": dict(vi="Xuyên thấu (Piercing Line)", short="Xuyên thấu", type="bullish", candles=2,
        text="Sau nến giảm dài, nến tăng mở thấp rồi đóng cửa vượt quá nửa thân nến giảm. "
             "Phe mua phản công mạnh, là tín hiệu đảo chiều tăng."),
    "dark_cloud_cover": dict(vi="Mây đen bao phủ (Dark Cloud Cover)", short="Mây đen", type="bearish", candles=2,
        text="Sau nến tăng dài, nến giảm mở cao rồi đóng cửa thấp hơn nửa thân nến tăng. "
             "Phe bán áp đảo, là tín hiệu đảo chiều giảm."),
    "three_white_soldiers": dict(vi="Ba chàng lính trắng (Three White Soldiers)", short="3 Lính trắng", type="bullish", candles=3,
        text="Ba nến tăng liên tiếp, thân dài, mỗi nến đóng cao hơn nến trước và gần mức cao nhất. "
             "Lực mua bền bỉ, báo hiệu xu hướng tăng đang hình thành."),
    "three_black_crows": dict(vi="Ba con quạ đen (Three Black Crows)", short="3 Quạ đen", type="bearish", candles=3,
        text="Ba nến giảm liên tiếp, thân dài, mỗi nến đóng thấp hơn nến trước và gần mức thấp nhất. "
             "Lực bán áp đảo, báo hiệu xu hướng giảm đang hình thành."),
}

TREND_VI = {"up": "tăng", "down": "giảm", "side": "đi ngang"}


def _trend(c, j):
    """Xu hướng tại phiên j, dựa trên % thay đổi giá đóng cửa sau TREND_LOOKBACK phiên."""
    if j - TREND_LOOKBACK < 0 or not c[j - TREND_LOOKBACK]:
        return "side", 0.0
    chg = float(c[j] / c[j - TREND_LOOKBACK] - 1)
    if chg > TREND_THRESHOLD:
        return "up", chg
    if chg < -TREND_THRESHOLD:
        return "down", chg
    return "side", chg


def _confidence(score):
    return "cao" if score >= 3 else "trung bình" if score == 2 else "thấp"


def detect_patterns(df: pd.DataFrame) -> list:
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    times = df["time"].dt.strftime("%Y-%m-%d").tolist()
    n = len(df)

    body = np.abs(c - o)
    rng = h - l
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l
    avg_body = pd.Series(body).rolling(14, min_periods=5).mean().to_numpy()
    vol_avg = pd.Series(v).rolling(20, min_periods=5).mean().to_numpy()
    bull, bear = c > o, c < o

    found = []

    def add(i, key, trend, chg, shape_strong):
        meta = META[key]
        base = 0 if meta["candles"] == 1 else 1
        vol_ratio = v[i] / vol_avg[i] if vol_avg[i] and not np.isnan(vol_avg[i]) else 0
        score = base + int(abs(chg) >= STRONG_TREND) + int(bool(shape_strong)) + int(vol_ratio >= 1.2)
        context = (f"Xuất hiện sau xu hướng {TREND_VI[trend]} ({chg * 100:+.1f}% trong {TREND_LOOKBACK} phiên trước). "
                   f"Volume phiên này = {vol_ratio:.1f}x trung bình 20 phiên.")
        found.append({
            "index": int(i), "time": times[i], "key": key,
            "name_vi": meta["vi"], "short": meta["short"], "type": meta["type"],
            "confidence": _confidence(score), "score": int(score),
            "explanation": meta["text"], "context": context,
            "price": float(h[i] if meta["type"] != "bullish" else l[i]),
        })

    for i in range(2, n):
        if any(np.isnan(x[i]) for x in (o, h, l, c)) or np.isnan(avg_body[i]) or avg_body[i] == 0:
            continue
        avg = avg_body[i]
        is_long = lambda k: body[k] >= 0.9 * avg
        is_small = lambda k: body[k] <= 0.5 * avg

        # ---------- 1 nến ----------
        if rng[i] > 0:
            trend, chg = _trend(c, i - 1)
            if body[i] <= 0.1 * rng[i]:
                if trend in ("up", "down"):
                    add(i, "doji", trend, chg, body[i] <= 0.05 * rng[i])
            else:
                hammer_shape = lower[i] >= 2 * body[i] and upper[i] <= 0.1 * rng[i]
                inv_shape = upper[i] >= 2 * body[i] and lower[i] <= 0.1 * rng[i]
                if hammer_shape and trend == "down":
                    add(i, "hammer", trend, chg, lower[i] >= 3 * body[i])
                elif inv_shape and trend == "down":
                    add(i, "inverted_hammer", trend, chg, upper[i] >= 3 * body[i])
                elif inv_shape and trend == "up":
                    add(i, "shooting_star", trend, chg, upper[i] >= 3 * body[i])

        # ---------- 2 nến ----------
        p = i - 1
        if body[p] > 0:
            trend, chg = _trend(c, i - 2)
            mid = (o[p] + c[p]) / 2
            if trend == "down" and bear[p] and bull[i]:
                if o[i] <= c[p] and c[i] >= o[p] and body[i] > body[p]:
                    add(i, "bullish_engulfing", trend, chg, body[i] >= 1.5 * body[p])
                elif is_long(p) and o[i] > c[p] and c[i] < o[p] and body[i] <= 0.6 * body[p]:
                    add(i, "bullish_harami", trend, chg, body[i] <= 0.3 * body[p])
                elif is_long(p) and o[i] <= c[p] and mid < c[i] < o[p]:
                    add(i, "piercing_line", trend, chg, c[i] >= o[p] - 0.25 * body[p])
            elif trend == "up" and bull[p] and bear[i]:
                if o[i] >= c[p] and c[i] <= o[p] and body[i] > body[p]:
                    add(i, "bearish_engulfing", trend, chg, body[i] >= 1.5 * body[p])
                elif is_long(p) and o[i] < c[p] and c[i] > o[p] and body[i] <= 0.6 * body[p]:
                    add(i, "bearish_harami", trend, chg, body[i] <= 0.3 * body[p])
                elif is_long(p) and o[i] >= c[p] and o[p] < c[i] < mid:
                    add(i, "dark_cloud_cover", trend, chg, c[i] <= o[p] + 0.25 * body[p])

        # ---------- 3 nến ----------
        if i >= 2:
            a, b = i - 2, i - 1
            trend, chg = _trend(c, i - 3)
            mid_a = (o[a] + c[a]) / 2
            mid_b = (o[b] + c[b]) / 2

            if trend == "down" and bear[a] and is_long(a) and is_small(b) and mid_b < mid_a \
                    and bull[i] and c[i] > mid_a:
                add(i, "morning_star", trend, chg, c[i] >= o[a])
            elif trend == "up" and bull[a] and is_long(a) and is_small(b) and mid_b > mid_a \
                    and bear[i] and c[i] < mid_a:
                add(i, "evening_star", trend, chg, c[i] <= o[a])

            if trend != "up" and bull[a] and bull[b] and bull[i] \
                    and c[b] > c[a] and c[i] > c[b] \
                    and o[a] < o[b] <= c[a] and o[b] < o[i] <= c[b] \
                    and all(body[k] >= 0.8 * avg and upper[k] <= 0.3 * body[k] for k in (a, b, i)):
                add(i, "three_white_soldiers", trend, chg, v[a] <= v[b] <= v[i])
            elif trend != "down" and bear[a] and bear[b] and bear[i] \
                    and c[b] < c[a] and c[i] < c[b] \
                    and c[a] <= o[b] < o[a] and c[b] <= o[i] < o[b] \
                    and all(body[k] >= 0.8 * avg and lower[k] <= 0.3 * body[k] for k in (a, b, i)):
                add(i, "three_black_crows", trend, chg, v[a] <= v[b] <= v[i])

    return found