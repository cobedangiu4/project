from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .data_service import fetch_history
from .indicators import compute_indicators, explain_latest
from .patterns import detect_patterns
from .recommendation import recommend

app = FastAPI(title="VN Stock Analyzer", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stock/{symbol}")
def get_stock(symbol: str, days: int = Query(700, ge=250, le=3000)):
    try:
        df = fetch_history(symbol, days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if len(df) < 30:
        raise HTTPException(status_code=422, detail="Dữ liệu quá ít để phân tích.")

    df = compute_indicators(df)
    analysis = explain_latest(df)
    patterns = detect_patterns(df)
    recommendation = recommend(df, analysis, patterns)

    out = df.copy()
    out["time"] = out["time"].dt.strftime("%Y-%m-%d")
    out = out.astype(object).where(out.notna(), None)  # NaN -> null cho JSON

    return {
        "symbol": symbol.upper(),
        "count": len(out),
        "last_date": out["time"].iloc[-1],
        "last_close": out["close"].iloc[-1],
        "analysis": analysis,
        "patterns": patterns,
        "recommendation": recommendation,
        "candles": out.to_dict(orient="records"),
    }


# Phục vụ giao diện web. Phải đặt SAU các route /api.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)