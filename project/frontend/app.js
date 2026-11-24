const API_BASE = location.protocol === "file:" ? "http://localhost:8000" : "";
const $ = (s) => document.querySelector(s);

const COLORS = { grid: "#1b2840", text: "#8da0bd", up: "#22c55e", down: "#ef4444" };
const CLS = { Mua: "buy", "Bán": "sell", "Chờ": "wait" };

const charts = {};
const S = {};          // các series
const state = { data: null };

// ---------------------------------------------------------------- khởi tạo biểu đồ
function makeChart(el, height) {
  return LightweightCharts.createChart(el, {
    width: el.clientWidth,
    height,
    layout: { background: { type: "solid", color: "transparent" }, textColor: COLORS.text },
    grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
    rightPriceScale: { borderColor: COLORS.grid, minimumWidth: 70 },
    timeScale: { borderColor: COLORS.grid },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });
}

function line(chart, color, extra = {}) {
  return chart.addLineSeries({
    color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, ...extra,
  });
}

function initCharts() {
  charts.main = makeChart($("#chartMain"), 460);
  S.candle = charts.main.addCandlestickSeries({
    upColor: COLORS.up, downColor: COLORS.down, borderVisible: false,
    wickUpColor: COLORS.up, wickDownColor: COLORS.down,
  });
  S.volume = charts.main.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "" });
  charts.main.priceScale("").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

  S.sma20 = line(charts.main, "#facc15");
  S.sma50 = line(charts.main, "#38bdf8");
  S.sma200 = line(charts.main, "#f472b6");
  S.ema12 = line(charts.main, "#a78bfa", { visible: false });
  S.ema26 = line(charts.main, "#fb923c", { visible: false });
  S.bbUpper = line(charts.main, "#94a3b8", { lineStyle: 2, visible: false });
  S.bbLower = line(charts.main, "#94a3b8", { lineStyle: 2, visible: false });

  charts.rsi = makeChart($("#chartRsi"), 140);
  S.rsi = line(charts.rsi, "#38bdf8", {
    lineWidth: 2,
    autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }),
  });
  S.rsi.createPriceLine({ price: 70, color: COLORS.down, lineStyle: 2, lineWidth: 1, axisLabelVisible: true, title: "" });
  S.rsi.createPriceLine({ price: 30, color: COLORS.up, lineStyle: 2, lineWidth: 1, axisLabelVisible: true, title: "" });

  charts.macd = makeChart($("#chartMacd"), 160);
  S.hist = charts.macd.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });
  S.macd = line(charts.macd, "#38bdf8", { lineWidth: 2 });
  S.signal = line(charts.macd, "#fb923c", { lineWidth: 2 });

  // Đồng bộ thanh cuộn/zoom giữa 3 biểu đồ
  const all = [charts.main, charts.rsi, charts.macd];
  let syncing = false;
  all.forEach((src) => {
    src.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (syncing || !range) return;
      syncing = true;
      all.forEach((t) => { if (t !== src) t.timeScale().setVisibleLogicalRange(range); });
      syncing = false;
    });
  });

  window.addEventListener("resize", () => {
    charts.main.applyOptions({ width: $("#chartMain").clientWidth });
    charts.rsi.applyOptions({ width: $("#chartRsi").clientWidth });
    charts.macd.applyOptions({ width: $("#chartMacd").clientWidth });
  });
}

// ---------------------------------------------------------------- tiện ích
// Điểm không có giá trị -> whitespace, để 3 biểu đồ luôn cùng số điểm và đồng bộ đúng
const toLine = (data, key) =>
  data.map((d) => (d[key] == null ? { time: d.time } : { time: d.time, value: d[key] }));

const fmt = (x, d = 2) => Number(x).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
const confClass = (c) => (c === "cao" ? "conf-cao" : c === "trung bình" ? "conf-trung" : "conf-thap");
const typeLabel = { bullish: "Tăng", bearish: "Giảm", neutral: "Trung lập" };

function setStatus(msg, isError = false) {
  const el = $("#status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
  el.hidden = !msg;
}

// ---------------------------------------------------------------- vẽ dữ liệu
function renderCharts(d) {
  const c = d.candles;
  S.candle.setData(c.map((x) => ({ time: x.time, open: x.open, high: x.high, low: x.low, close: x.close })));
  S.volume.setData(c.map((x) => ({
    time: x.time, value: x.volume,
    color: x.close >= x.open ? "rgba(34,197,94,.35)" : "rgba(239,68,68,.35)",
  })));
  for (const k of ["sma20", "sma50", "sma200", "ema12", "ema26"]) S[k].setData(toLine(c, k));
  S.bbUpper.setData(toLine(c, "bb_upper"));
  S.bbLower.setData(toLine(c, "bb_lower"));
  S.rsi.setData(toLine(c, "rsi14"));
  S.macd.setData(toLine(c, "macd"));
  S.signal.setData(toLine(c, "macd_signal"));
  S.hist.setData(c.map((x) => x.macd_hist == null
    ? { time: x.time }
    : { time: x.time, value: x.macd_hist, color: x.macd_hist >= 0 ? "rgba(34,197,94,.6)" : "rgba(239,68,68,.6)" }));

  renderMarkers();
  const n = c.length;
  charts.main.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - 130), to: n + 4 });
}

function visiblePatterns() {
  const showLow = $("#showLow").checked;
  return state.data.patterns.filter((p) => showLow || p.confidence !== "thấp");
}

function renderMarkers() {
  const ms = visiblePatterns().map((p) => ({
    time: p.time,
    position: p.type === "bullish" ? "belowBar" : "aboveBar",
    color: p.type === "bullish" ? COLORS.up : p.type === "bearish" ? COLORS.down : "#eab308",
    shape: p.type === "bullish" ? "arrowUp" : p.type === "bearish" ? "arrowDown" : "circle",
    text: p.short + (p.confidence === "cao" ? " ★" : ""),
  }));
  ms.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
  S.candle.setMarkers(ms);
  renderPatternList();
}

function renderHero(d) {
  const c = d.candles;
  const last = c[c.length - 1], prev = c[c.length - 2];
  const chg = last.close - prev.close, pct = (chg / prev.close) * 100;
  $("#heroSymbol").textContent = d.symbol;
  $("#heroPrice").innerHTML = `${fmt(last.close)} <small>nghìn đ</small>`;
  $("#heroSub").innerHTML =
    `<span class="${chg >= 0 ? "up" : "down"}">${chg >= 0 ? "▲" : "▼"} ${fmt(Math.abs(chg))} (${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%)</span> · Phiên ${d.last_date}`;
}

function renderRecommendation(r) {
  const cls = CLS[r.action];
  const reasons = r.reasons.length
    ? r.reasons.map((x) => `<li><span class="dot ${x.effect}"></span><span><b>${x.source}:</b> ${x.text}</span></li>`).join("")
    : `<li class="empty">Chưa có tín hiệu nổi bật.</li>`;
  $("#recCard").innerHTML = `
    <div class="rec-head">
      <div class="rec-badge ${cls}">${r.action.toUpperCase()}</div>
      <div class="rec-meta">Mức độ: <b>${r.strength}</b> · Điểm tổng hợp: <b>${r.score}</b><br>${r.summary}</div>
    </div>
    <ul class="reasons">${reasons}</ul>
    <div class="disclaimer">⚠ ${r.disclaimer}</div>`;
}

function renderPatternList() {
  const list = visiblePatterns().slice().reverse().slice(0, 40);
  const box = $("#patternList");
  if (!list.length) {
    box.innerHTML = `<div class="empty">Không phát hiện mô hình nào (thử bật "Hiện cả mô hình độ tin cậy thấp").</div>`;
    return;
  }
  box.innerHTML = list.map((p, i) => `
    <div class="item clickable" data-i="${i}">
      <div class="item-head">
        <span class="item-title">${p.name_vi}</span>
        <span class="badge ${p.type}">${typeLabel[p.type]}</span>
      </div>
      <div class="date">${p.time} · Độ tin cậy: <b class="${confClass(p.confidence)}">${p.confidence}</b></div>
      <div>${p.explanation}</div>
      <div class="ctx">${p.context}</div>
    </div>`).join("");
  box.querySelectorAll(".item").forEach((el) => {
    el.addEventListener("click", () => {
      const p = list[Number(el.dataset.i)];
      charts.main.timeScale().setVisibleLogicalRange({ from: p.index - 45, to: p.index + 45 });
      $("#chartMain").scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });
}

function card(title, signal, lines) {
  const badge = signal
    ? `<span class="badge ${CLS[signal] || "muted"}">${signal}</span>` : "";
  return `<div class="item"><div class="item-head"><span class="item-title">${title}</span>${badge}</div>
    ${lines.map((l) => `<div>${l}</div>`).join("")}</div>`;
}

function renderIndicators(a) {
  const html = [];
  html.push(card("RSI (14)", a.rsi.signal, [a.rsi.text]));
  html.push(card("SMA 20 / 50 / 200", null, a.sma.map((s) => s.text)));
  html.push(card("EMA 12 / 26", a.ema.signal, [
    `EMA12 = ${fmt(a.ema.ema12)}, EMA26 = ${fmt(a.ema.ema26)}`, a.ema.text]));
  html.push(card("MACD", a.macd.signal, [a.macd.text]));
  html.push(card("Bollinger Bands (20, 2)", a.bollinger.signal, [
    a.bollinger.upper != null
      ? `Dải trên ${fmt(a.bollinger.upper)} · Giữa ${fmt(a.bollinger.middle)} · Dưới ${fmt(a.bollinger.lower)}` : "",
    a.bollinger.text].filter(Boolean)));
  html.push(card("Volume trung bình (20 phiên)", null, [a.volume.text]));
  $("#indicatorList").innerHTML = html.join("");
}

// ---------------------------------------------------------------- gọi API
async function load(symbol) {
  symbol = symbol.trim().toUpperCase();
  if (!symbol) return;
  $("#symbol").value = symbol;
  setStatus(`Đang tải dữ liệu ${symbol}...`);
  try {
    const res = await fetch(`${API_BASE}/api/stock/${encodeURIComponent(symbol)}`);
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "Lỗi không xác định");
    state.data = json;
    $("#result").hidden = false;   // hiện trước để biểu đồ đo đúng chiều rộng
    ["main", "rsi", "macd"].forEach((k) =>
      charts[k].applyOptions({ width: $(`#chart${k[0].toUpperCase() + k.slice(1)}`).clientWidth }));
    renderHero(json);
    renderRecommendation(json.recommendation);
    renderCharts(json);
    renderIndicators(json.analysis);
    setStatus("");
  } catch (e) {
    setStatus(`Lỗi: ${e.message}`, true);
  }
}

// ---------------------------------------------------------------- sự kiện
document.addEventListener("DOMContentLoaded", () => {
  initCharts();

  $("#chips").innerHTML = ["VCB", "FPT", "HPG", "VNM", "VIC", "MWG", "TCB", "SSI"]
    .map((s) => `<span class="chip" data-s="${s}">${s}</span>`).join("");
  $("#chips").addEventListener("click", (e) => { if (e.target.dataset.s) load(e.target.dataset.s); });

  $("#searchForm").addEventListener("submit", (e) => { e.preventDefault(); load($("#symbol").value); });

  document.querySelectorAll("[data-line]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const k = cb.dataset.line;
      if (k === "bb") {
        S.bbUpper.applyOptions({ visible: cb.checked });
        S.bbLower.applyOptions({ visible: cb.checked });
      } else {
        S[k].applyOptions({ visible: cb.checked });
      }
    });
  });

  $("#showLow").addEventListener("change", () => state.data && renderMarkers());
});