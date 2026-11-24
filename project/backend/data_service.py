from datetime import date, timedelta

import pandas as pd
from vnstock import Vnstock

# Thử lần lượt các nguồn dữ liệu, nguồn nào lỗi thì chuyển sang nguồn kế tiếp
SOURCES = ["VCI", "TCBS"]


def fetch_history(symbol: str, days: int = 700) -> pd.DataFrame:
    """Lấy dữ liệu nến ngày. 700 ngày lịch ≈ 480 phiên, đủ để tính SMA200."""
    end = date.today()
    start = end - timedelta(days=days)
    last_error = None

    for source in SOURCES:
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source=source)
            df = stock.quote.history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval="1D",
            )
            if df is not None and not df.empty:
                return _normalize(df)
        except (Exception, SystemExit) as e:  # vnstock đôi khi dùng SystemExit khi bị giới hạn request
            last_error = e

    raise ValueError(
        f"Không lấy được dữ liệu cho mã '{symbol}'. Kiểm tra lại mã hoặc thử lại sau. "
        f"Chi tiết: {last_error}"
    )


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["time", "open", "high", "low", "close", "volume"]]