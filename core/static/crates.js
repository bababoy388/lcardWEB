// ============================================================
// Тема
// ============================================================
function toggleTheme() {
  const html = document.documentElement;
  const cur = html.getAttribute('data-theme');
  html.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark');
}

// ============================================================
// API
// ============================================================
async function apiGet(url) {
  const r = await fetch(url);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
  return data;
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
  return data;
}

async function apiDelete(url) {
  const r = await fetch(url, { method: 'DELETE' });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
  return data;
}

// ============================================================
// Подключённые крейты
// ============================================================
async function loadCrates() {
  const box = document.getElementById('cratesList');
  const cnt = document.getElementById('cratesCount');

  try {
    const d = await apiGet('/api/ltrd/crates');
    const list = d.crates || [];

    cnt.textContent = list.length;

    if (!list.length) {
      box.innerHTML = '<div class="empty-row">Крейты не найдены</div>';
      return;
    }

    box.innerHTML = '';
    for (const c of list) {
      const item = document.createElement('div');
      item.className = 'crate-item';
      item.innerHTML = `
        <span class="status-dot"></span>
        <span class="crate-csn">${escapeHtml(c.csn || '—')}</span>
        <span class="crate-badge">подключён</span>
      `;
      box.appendChild(item);
    }
  } catch (e) {
    box.innerHTML = `<div class="empty-row">Ошибка: ${escapeHtml(e.message)}</div>`;
    cnt.textContent = '—';
  }
}

// ============================================================
// IP-адреса ltrd
// ============================================================
function statusLabel(code) {
  // Примерные статусы из en_LTR_CrateIpStatus
  switch (code) {
    case 0:  return { txt: 'Не подключён', cls: 'idle' };
    case 1:  return { txt: 'Подключён',    cls: 'ok' };
    case 2:  return { txt: 'Ошибка',       cls: 'error' };
    case 3:  return { txt: 'Не найден',    cls: 'error' };
    default: return { txt: 'Статус ' + code, cls: 'unknown' };
  }
}

async function loadIps() {
  const tbody = document.getElementById('ipTbody');
  const cnt   = document.getElementById('ipCount');

  try {
    const d = await apiGet('/api/ltrd/ip');
    const list = d.entries || [];

    cnt.textContent = list.length;

    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Записей нет</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    for (const e of list) {
      const st = statusLabel(e.status);

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="col-ip">${escapeHtml(e.ip)}</td>
        <td class="col-csn">${escapeHtml(e.csn || '—')}</td>
        <td><span class="status-badge ${st.cls}">${st.txt}</span></td>
        <td><span class="check-mark ${e.autoconnect ? 'on' : 'off'}">${e.autoconnect ? '✓' : '—'}</span></td>
        <td><span class="check-mark ${e.reconnect ? 'on' : 'off'}">${e.reconnect ? '✓' : '—'}</span></td>
        <td class="col-actions">
          <button class="btn-del" data-ip="${escapeHtml(e.ip)}">🗑 Удалить</button>
        </td>
      `;
      tbody.appendChild(tr);
    }

    // Навешиваем обработчики на кнопки удаления
    tbody.querySelectorAll('.btn-del').forEach(btn => {
      btn.addEventListener('click', () => deleteIp(btn.dataset.ip));
    });

  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-row">Ошибка: ${escapeHtml(e.message)}</td></tr>`;
    cnt.textContent = '—';
  }
}

// ============================================================
// Добавление IP
// ============================================================
async function addIp() {
  const ipEl  = document.getElementById('newIp');
  const info  = document.getElementById('addIpInfo');
  const ip    = ipEl.value.trim();

  if (!ip) {
    setInfo(info, 'Введите IP-адрес', 'err');
    return;
  }

  // Валидация формата
  const re = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
  const m = ip.match(re);
  if (!m || m.slice(1).some(n => parseInt(n) > 255)) {
    setInfo(info, 'Неверный формат IP', 'err');
    return;
  }

  const payload = {
    ip: ip,
    autoconnect: document.getElementById('chkAutoconnect').checked,
    reconnect:   document.getElementById('chkReconnect').checked,
    permanent:   document.getElementById('chkPermanent').checked,
  };

  setInfo(info, 'Отправка…', '');

  try {
    await apiPost('/api/ltrd/ip', payload);
    setInfo(info, '✓ Добавлено', 'ok');
    ipEl.value = '';
    setTimeout(() => { info.textContent = ''; }, 3000);

    // Перезагружаем оба списка
    loadIps();
    loadCrates();
  } catch (e) {
    setInfo(info, 'Ошибка: ' + e.message, 'err');
  }
}

function setInfo(el, text, cls) {
  el.textContent = text;
  el.className = 'form-info ' + (cls || '');
}

// ============================================================
// Удаление IP
// ============================================================
async function deleteIp(ip) {
  if (!confirm(`Удалить IP-адрес ${ip} из конфигурации ltrd?`)) return;

  try {
    await apiDelete('/api/ltrd/ip?ip=' + encodeURIComponent(ip) + '&permanent=true');
    loadIps();
    loadCrates();
  } catch (e) {
    alert('Не удалось удалить: ' + e.message);
  }
}

// ============================================================
// Загрузка всего
// ============================================================
function loadAll() {
  loadCrates();
  loadIps();
}

// ============================================================
// Утилиты
// ============================================================
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
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
  } catch (_) {}
}

// ============================================================
// Инициализация
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  startUptime();
  pollStatus();
  setInterval(pollStatus, 2000);

  loadAll();

  // Enter в поле IP = добавление
  document.getElementById('newIp')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') addIp();
  });

  // R = обновить
  document.addEventListener('keydown', e => {
    if (e.key.toLowerCase() === 'r' &&
        !e.ctrlKey &&
        document.activeElement.tagName !== 'INPUT') {
      loadAll();
    }
  });
});