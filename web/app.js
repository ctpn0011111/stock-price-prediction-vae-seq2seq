// =============== CONFIG ===============
const BASE_URL = ""; // đổi thành "/api" nếu backend mount API dưới /api

// ===== THEME from CSS variables =====

// ===== THEME from CSS variables =====
function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return v || fallback;
}
function getTheme() {
  return {
    text: cssVar("--text", "#111827"),
    bg: cssVar("--bg", "#ffffff"),
    card: cssVar("--card", "#ffffff"),
    grid: cssVar("--border", "#e5e7eb"),
    muted: cssVar("--muted", "#6b7280"),
    accent: cssVar("--accent", "#2563eb"),
  };
}
// =============== HELPERS ===============
function fmtPct(x, d = 2) {
  return x == null || isNaN(x) ? "—" : `${x.toFixed(d)}%`;
}
function fmtNum(x, d = 2) {
  return x == null || isNaN(x) ? "—" : x.toFixed(d);
}
function toDateStr(d) {
  const dt = new Date(d);
  return Number.isNaN(dt.getTime()) ? d : dt.toISOString().slice(0, 10);
}
const $ = (id) => document.getElementById(id);

// =============== DOM ===============
const symbolSelect = $("symbolSelect");
const btDaysInput = $("btDays");
const chartTitleEl = $("chartTitle");

const rmseEl = $("rmseVal");
const mapeEl = $("mapeVal");
const daEl = $("daVal");
const taEl = $("taVal");
const sdaEl = $("sdaVal");
const daysEl = $("daysVal");

// =============== API ===============
async function apiGet(path, signal) {
  const res = await fetch(`${BASE_URL}${path}`, { cache: "no-store", signal });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return res.json();
}
async function loadSymbols() {
  const data = await apiGet("/symbols");
  const list = Array.isArray(data) ? data : data.symbols || [];
  symbolSelect.innerHTML = "";
  for (const s of list) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    symbolSelect.appendChild(opt);
  }
}
async function loadInfer(symbol, backtestDays, signal) {
  const q = new URLSearchParams({
    symbol,
    backtest_days: String(backtestDays),
  });
  return apiGet(`/infer?${q.toString()}`, signal);
}

// =============== RENDER METRICS ===============
function renderMetrics(m) {
  rmseEl.textContent = fmtNum(m.rmse);
  mapeEl.textContent = fmtPct(m.mape);
  daEl.textContent = fmtNum(m.da);
  taEl.textContent = fmtNum(m.ta);
  sdaEl.textContent = fmtNum(m.sda);
  daysEl.textContent = String(m.days ?? "—");
}

// =============== RENDER CHARTS (4 ô) ===============
function renderChartsSeparated(symbol, data) {
  const THEME = getTheme();
  const t = (data.backtest_df || []).map((d) => d.time.slice(0, 10));
  const y = (data.backtest_df || []).map((d) => d.actual);
  const p1 = (data.backtest_df || []).filter((d) =>
    Number.isFinite(d?.pred_1step)
  );
  const t1 = p1.map((d) => d.time.slice(0, 10));
  const y1 = p1.map((d) => d.pred_1step);
  const tf = (data.future_df || []).map((d) => d.time.slice(0, 10));
  const yf = (data.future_df || []).map((d) => d.pred_price);

  const ema20 = (data.backtest_df || []).map((d) => d.ema20 ?? null);
  const ema60 = (data.backtest_df || []).map((d) => d.ema60 ?? null);
  const ma10 = (data.backtest_df || []).map((d) => d.ma10 ?? null);
  const ma20 = (data.backtest_df || []).map((d) => d.ma20 ?? null);
  const vol = (data.backtest_df || []).map((d) => d.volume ?? null);
  const rsi = (data.backtest_df || []).map((d) => d.rsi_14 ?? null);
  const macd = (data.backtest_df || []).map((d) => d.macd ?? null);
  const sig = (data.backtest_df || []).map((d) => d.macd_signal ?? null);
  const mch = (data.backtest_df || []).map((d) => d.macd_hist ?? null);

  const commonLayout = (title, ytitle) => ({
    paper_bgcolor: THEME.card,
    plot_bgcolor: THEME.card,
    font: { color: THEME.text },
    margin: { t: 30, r: 40, b: 40, l: 60 },
    xaxis: { gridcolor: THEME.grid, showspikes: true, spikemode: "across" },
    yaxis: { gridcolor: THEME.grid, title: ytitle },
    showlegend: true,
    title: {
      text: title,
      x: 0,
      xanchor: "left",
      font: { size: 14, color: THEME.muted },
    },
  });

  // Price
  // Price (đã loại bỏ EMA/MA)
  Plotly.react(
    "priceChart",
    [
      { x: t, y, name: "Actual (history)", mode: "lines" },
      {
        x: t1,
        y: y1,
        name: "1-step stitched",
        mode: "lines",
        line: { dash: "dash" },
      },
      {
        x: tf,
        y: yf,
        name: `Forecast (+${yf.length})`,
        mode: "lines",
        line: { dash: "dot" },
      },
    ],
    commonLayout("Giá & Forecast", "Price"),
    { responsive: true }
  );

  // Volume
  Plotly.react(
    "volumeChart",
    [
      {
        x: t,
        y: vol,
        type: "bar",
        name: "Volume",
        opacity: 0.6,
        marker: { color: THEME.accent },
      },
    ],
    commonLayout("Khối lượng", "Volume"),
    { responsive: true }
  );

  // RSI
  const rsiLayout = commonLayout("RSI(14)", "RSI");
  rsiLayout.yaxis.range = [0, 100];
  rsiLayout.shapes = [
    {
      type: "line",
      x0: 0,
      x1: 1,
      xref: "paper",
      yref: "y",
      y0: 30,
      y1: 30,
      line: { dash: "dot", width: 1, color: THEME.muted },
    },
    {
      type: "line",
      x0: 0,
      x1: 1,
      xref: "paper",
      yref: "y",
      y0: 70,
      y1: 70,
      line: { dash: "dot", width: 1, color: THEME.muted },
    },
  ];
  Plotly.react(
    "rsiChart",
    [{ x: t, y: rsi, name: "RSI(14)", mode: "lines" }],
    rsiLayout,
    { responsive: true }
  );

  // MACD
  Plotly.react(
    "macdChart",
    [
      { x: t, y: macd, name: "MACD", mode: "lines" },
      { x: t, y: sig, name: "Signal", mode: "lines" },
      { x: t, y: mch, name: "MACD Hist", type: "bar", opacity: 0.45 },
    ],
    commonLayout("MACD", "MACD"),
    { responsive: true }
  );

  // Đồng bộ zoom/drag theo trục X giữa 4 charts
  linkPlots(["priceChart", "volumeChart", "rsiChart", "macdChart"]);

  // Tự resize khi thay đổi kích thước cửa sổ
  setupAutoResize(["priceChart", "volumeChart", "rsiChart", "macdChart"]);
}

// Liên kết zoom trục X giữa nhiều biểu đồ
function linkPlots(ids) {
  const graphs = ids.map((id) => document.getElementById(id));
  graphs.forEach((g, i) => {
    g.on("plotly_relayout", (ev) => {
      const min = ev["xaxis.range[0]"],
        max = ev["xaxis.range[1]"];
      if (min == null || max == null) return;
      graphs.forEach((other, j) => {
        if (j === i) return;
        Plotly.relayout(other, {
          "xaxis.range[0]": min,
          "xaxis.range[1]": max,
        });
      });
    });
  });
}

// Resize tiện lợi
function setupAutoResize(ids) {
  const graphs = ids.map((id) => document.getElementById(id));
  let raf;
  const onResize = () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() =>
      graphs.forEach((g) => g && Plotly.Plots.resize(g))
    );
  };
  window.removeEventListener("resize", window.__plotResize);
  window.addEventListener("resize", onResize);
  window.__plotResize = onResize;
}

// =============== LOAD FLOW ===============
let aborter = null;

async function refresh() {
  const symbol = symbolSelect.value;
  const btDays = Number(btDaysInput.value || 60);
  if (!symbol) return;

  if (aborter) aborter.abort();
  aborter = new AbortController();

  try {
    const data = await loadInfer(symbol, btDays, aborter.signal);
    renderMetrics(data.metrics_backtest || {});
    renderChartsSeparated(symbol, data);
  } catch (err) {
    if (err.name !== "AbortError") {
      console.error(err);
      alert("Không tải được dữ liệu. Kiểm tra API /symbols và /infer.");
    }
  }
}

async function init() {
  await loadSymbols();
  symbolSelect.addEventListener("change", refresh);
  btDaysInput.addEventListener("input", refresh);
  if (symbolSelect.options.length > 0) {
    symbolSelect.selectedIndex = 0;
    await refresh();
  }
}

window.addEventListener("load", init);
