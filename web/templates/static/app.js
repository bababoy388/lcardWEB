// ============================================================
// Тема
// ============================================================
function toggleTheme() {
  const html = document.documentElement;
  const cur = html.getAttribute('data-theme');
  html.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark');
}

// ============================================================
// Состояние зума по каждому графику
// ============================================================
const zoomState = {
  wave: { xmin: null, xmax: null, ymin: null, ymax: null },
  fft:  { fmin: null, fmax: null },
  hist: { xmin: null, xmax: null },
};

// ============================================================
// Хелпер: query-строка с диапазоном
// ============================================================
function rangeParams() {
  const fromEl = document.getElementById('rangeFrom');
  const toEl   = document.getElementById('rangeTo');
  const p = new URLSearchParams();
  if (fromEl.value && toEl.value) {
    p.set('from', fromEl.value);
    p.set('to',   toEl.value);
  }
  return p;
}

// ============================================================
// Загрузка графиков
// ============================================================
function loadAllPlots() {
  loadWave();
  loadFft();
  loadHist();
  loadStats();
}

function loadLatestPlots() {
  document.getElementById('rangeFrom').value = '';
  document.getElementById('rangeTo').value = '';
  zoomState.wave = { xmin: null, xmax: null, ymin: null, ymax: null };
  zoomState.fft  = { fmin: null, fmax: null };
  loadAllPlots();
  setRangeInfo('Загрузка последних данных…', '');
}

// ---------- Осциллограмма ----------
function loadWave() {
  const p = rangeParams();
  const z = zoomState.wave;
  if (z.xmin != null) p.set('xmin', z.xmin);
  if (z.xmax != null) p.set('xmax', z.xmax);
  if (z.ymin != null) p.set('ymin', z.ymin);
  if (z.ymax != null) p.set('ymax', z.ymax);

  const img = document.getElementById('waveImg');
  img.src = '/api/plot/wave?' + p.toString() + '&_=' + Date.now();

  img.onload = () => {
    const pts = img.naturalWidth;    // можно вытащить через X-Points, но так не выйдет — нужен fetch
    // Обновим мета-информацию после загрузки
    setRangeInfo('Осциллограмма обновлена', 'ok');
  };
}

// ---------- FFT ----------
function loadFft() {
  const p = rangeParams();
  const z = zoomState.fft;
  if (z.fmin != null) p.set('fmin', z.fmin);
  if (z.fmax != null) p.set('fmax', z.fmax);

  const img = document.getElementById('fftImg');
  img.src = '/api/plot/fft?' + p.toString() + '&_=' + Date.now();
}

// ---------- Гистограмма ----------
function loadHist() {
  const p = rangeParams();
  const ch = document.getElementById('histCh').value;
  p.set('ch', ch);
  const img = document.getElementById('histImg');
  img.src = '/api/plot/hist?' + p.toString() + '&_=' + Date.now();
}

// ---------- Статистика ----------
function loadStats() {
  const p = rangeParams();
  const img = document.getElementById('statsImg');
  img.src = '/api/plot/stats?' + p.toString() + '&_=' + Date.now();
}

// ============================================================
// Зум осциллограммы
// ============================================================
function setupWaveZoom() {
  const wrap    = document.getElementById('waveWrap');
  const overlay = document.getElementById('waveOverlay');
  const rectEl  = document.getElementById('waveRect');

  let startX = 0, startY = 0;
  let selecting = false;

  overlay.addEventListener('mousedown', e => {
    if (e.button !== 0) return;
    e.preventDefault();
    const r = wrap.getBoundingClientRect();
    startX = e.clientX - r.left;
    startY = e.clientY - r.top;
    selecting = true;
    rectEl.style.left   = startX + 'px';
    rectEl.style.top    = startY + 'px';
    rectEl.style.width  = '0px';
    rectEl.style.height = '0px';
    rectEl.classList.add('active');
  });

  overlay.addEventListener('mousemove', e => {
    if (!selecting) return;
    const r = wrap.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    const x0 = Math.min(startX, x);
    const y0 = Math.min(startY, y);
    const w  = Math.abs(x - startX);
    const h  = Math.abs(y - startY);
    rectEl.style.left   = x0 + 'px';
    rectEl.style.top    = y0 + 'px';
    rectEl.style.width  = w + 'px';
    rectEl.style.height = h + 'px';
  });

  overlay.addEventListener('mouseup', e => {
    if (!selecting) return;
    selecting = false;
    rectEl.classList.remove('active');

    const r = wrap.getBoundingClientRect();
    const x1 = Math.min(startX, e.clientX - r.left);
    const x2 = Math.max(startX, e.clientX - r.left);
    const y1 = Math.min(startY, e.clientY - r.top);
    const y2 = Math.max(startY, e.clientY - r.top);

    if (x2 - x1 < 10 || y2 - y1 < 10) return;   // слишком маленькое выделение

    // Переводим пиксели в значения по осям
    // Для этого нужно знать xlim/ylim текущего графика.
    // Их мы запросим у сервера через тот же эндпоинт.
    // Простое решение: сервер возвращает X-Limits и Y-Limits в заголовках.
    fetchMeta('/api/plot/wave?' + rangeParams().toString())
      .then(meta => {
        if (!meta) return;
        const { xlim, ylim } = meta;
        if (!xlim || !ylim) return;

        const W = wrap.clientWidth;
        const H = wrap.clientHeight;

        const xmin = xlim[0] + (x2 - x1 === W ? 0 : (x1 / W) * (xlim[1] - xlim[0]));
        const xmax = xlim[0] + ((x2 / W) * (xlim[1] - xlim[0]));
        // Y инвертирован: 0 сверху — это ylim[1]
        const ymax = ylim[1] - (y1 / H) * (ylim[1] - ylim[0]);
        const ymin = ylim[1] - (y2 / H) * (ylim[1] - ylim[0]);

        zoomState.wave = { xmin, xmax, ymin, ymax };
        loadWave();
        setRangeInfo(`Zoom: X=[${xmin.toFixed(3)}, ${xmax.toFixed(3)}], Y=[${ymin.toFixed(3)}, ${ymax.toFixed(3)}]`, 'ok');
      });
  });

  // ПКМ — сброс зума
  overlay.addEventListener('contextmenu', e => {
    e.preventDefault();
    resetZoom();
  });
}

function resetZoom() {
  zoomState.wave = { xmin: null, xmax: null, ymin: null, ymax: null };
  zoomState.fft  = { fmin: null, fmax: null };
  loadAllPlots();
  setRangeInfo('Зум сброшен', 'ok');
}

async function fetchMeta(url) {
  try {
    const r = await fetch(url);
    const xlimHdr = r.headers.get('X-XLim');
    const ylimHdr = r.headers.get('X-YLim');
    if (!xlimHdr || !ylimHdr) return null;
    return {
      xlim: xlimHdr.split(',').map(Number),
      ylim: ylimHdr.split(',').map(Number),
    };
  } catch (_) { return null; }
}

// ============================================================
// Уведомление
// ============================================================
function setRangeInfo(text, cls) {
  const el = document.getElementById('rangeInfo');
  if (!el) return;
  el.textContent = text;
  el.className = 'range-info ' + (cls || '');
}

// ============================================================
// Uptime + статус
// ============================================================
function startUptime() {
  let s = 0;
  setInterval(() => {
    s++;
    const hh = String(Math.floor(s / 3600)).padStart(2, '0');
    const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
    const ss = String(s % 60).padStart(2, '0');
    const el = document.getElementById('uptime');
    if (el) el.textContent = `${hh}:${mm}:${ss}`;
  }, 1000);
}

async function pollStatus() {
  try {
    const r = await fetch('/api/status');
    if (!r.ok) return;
    const s = await r.json();
    const el = document.querySelector('.status-phase');
    if (el) el.textContent = s.phase || 'idle';
    const fEl = document.getElementById('currentFile');
    if (fEl && s.file_name) fEl.textContent = s.file_name;
  } catch (_) {}
}

// ============================================================
// Старт
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  startUptime();
  pollStatus();
  setInterval(pollStatus, 2000);

  setupWaveZoom();
  loadLatestPlots();
});