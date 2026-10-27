// ============================================================
// Тема
// ============================================================
function toggleTheme() {
  const html = document.documentElement;
  const cur = html.getAttribute('data-theme');
  html.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark');
}

// ============================================================
// Форматирование
// ============================================================
function fmtSize(bytes) {
  if (bytes < 1024) return bytes + ' Б';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' КиБ';
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' МиБ';
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' ГиБ';
}

function fmtDuration(sec) {
  if (sec < 0.001) return '< 1 мс';
  if (sec < 1) return (sec * 1000).toFixed(0) + ' мс';
  if (sec < 60) return sec.toFixed(3) + ' с';
  const m = Math.floor(sec / 60);
  const s = sec - m * 60;
  return `${m} мин ${s.toFixed(1)} с`;
}

function parseTs(s) {
  if (!s) return null;
  // "2026-10-13 13:10:30.123456" → Date
  return new Date(s.replace(' ', 'T'));
}

function fmtTs(s) {
  if (!s) return '—';
  return s;
}

// ============================================================
// Загрузка
// ============================================================
let allFiles = [];

async function loadFiles() {
  try {
    const r = await fetch('/api/files');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();

    allFiles = d.files || [];
    document.getElementById('dataDir').textContent = d.dir || '—';
    document.getElementById('dirInfo').textContent = d.dir || '—';

    renderFiles(allFiles);
  } catch (e) {
    document.getElementById('filesTbody').innerHTML =
      `<tr><td colspan="7" class="empty-row">Ошибка: ${e.message}</td></tr>`;
  }
}

// ============================================================
// Отрисовка
// ============================================================
function renderFiles(files) {
  const tbody = document.getElementById('filesTbody');
  document.getElementById('filesCount').textContent =
    `${files.length} ${plural(files.length, 'файл', 'файла', 'файлов')}`;

  const totalBytes = files.reduce((s, f) => s + (f.size || 0), 0);
  document.getElementById('totalSize').textContent = fmtSize(totalBytes);

  if (!files.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-row">Файлов не найдено</td></tr>';
    return;
  }

  tbody.innerHTML = '';

  for (const f of files) {
    const t1 = parseTs(f.ts_first);
    const t2 = parseTs(f.ts_last);
    const dur = (t1 && t2) ? (t2 - t1) / 1000 : null;

    const tr = document.createElement('tr');

    tr.innerHTML = `
      <td class="col-name">${escapeHtml(f.name)}</td>
      <td class="col-ts">${fmtTs(f.ts_first)}</td>
      <td class="col-ts">${fmtTs(f.ts_last)}</td>
      <td>${dur != null ? fmtDuration(dur) : '—'}</td>
      <td>${fmtSize(f.size || 0)}</td>
      <td>${escapeHtml(f.mtime_str || '')}</td>
      <td class="col-actions">
        <a class="btn-download" href="/api/files/download/${encodeURIComponent(f.name)}"
           download>⬇ Скачать</a>
      </td>
    `;
    tbody.appendChild(tr);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

// ============================================================
// Фильтр по имени
// ============================================================
function applyFilter(q) {
  if (!q) {
    renderFiles(allFiles);
    return;
  }
  const lower = q.toLowerCase();
  const filtered = allFiles.filter(f => f.name.toLowerCase().includes(lower));
  renderFiles(filtered);
}

// ============================================================
// Uptime
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
  } catch (_) {}
}

// ============================================================
// Инициализация
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  startUptime();
  pollStatus();
  setInterval(pollStatus, 2000);

  loadFiles();

  const filter = document.getElementById('filterInput');
  filter?.addEventListener('input', e => applyFilter(e.target.value));

  // Ctrl+F → фокус в поиск
  document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key.toLowerCase() === 'f') {
      e.preventDefault();
      filter?.focus();
    }
    if (e.key === 'Escape') {
      if (filter) filter.value = '';
      applyFilter('');
    }
    if (e.key.toLowerCase() === 'r' && !e.ctrlKey && document.activeElement !== filter) {
      loadFiles();
    }
  });
});